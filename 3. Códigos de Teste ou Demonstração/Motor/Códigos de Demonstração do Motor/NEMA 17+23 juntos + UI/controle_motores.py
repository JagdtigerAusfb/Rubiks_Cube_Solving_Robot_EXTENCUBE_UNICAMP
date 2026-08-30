#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
controle_motores.py
-------------------
Interface unica para dois motores de passo, cada um em uma porta USB:
  - esquerda : NEMA 17 + A4988
  - direita  : NEMA 23 + DM556

Os dois Arduinos rodam o mesmo sketch (controlador_passo.ino). O perfil do
driver (polaridade do ENABLE, microstep, etc.) e enviado por serial.

Requisitos:  pip install PyQt6 pyserial
Execucao:    python controle_motores.py
"""

import sys
import time

import serial
import serial.tools.list_ports
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFormLayout, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QSpinBox,
    QVBoxLayout, QWidget,
)

BAUDS = ["115200", "57600", "9600"]

PRESETS = {
    "A4988 / NEMA 17": {
        "micros": [1, 2, 4, 8, 16],
        "micro": 1,
        "enapol": 0,          # A4988: ENABLE ativo em LOW -> LOW habilita
        "vel": 800,
        "veli": 200,
        "acel": 4000,
        "passos": 200,
    },
    "DM556 / NEMA 23": {
        "micros": [1, 2, 4, 5, 8, 10, 16, 20, 25, 32, 40, 50, 64, 100, 125, 128],
        "micro": 8,
        "enapol": 1,          # anodo comum +5V: pino HIGH habilita
        "vel": 1600,
        "veli": 400,
        "acel": 8000,
        "passos": 1600,
    },
}

ESTADOS = {"0": "parado", "1": "movendo", "2": "pausa"}


# ---------------------------------------------------------------- leitor serial
class Leitor(QThread):
    """Le linhas da serial em segundo plano e repassa para a interface."""
    linha = pyqtSignal(str)
    caiu = pyqtSignal(str)

    def __init__(self, porta_serial):
        super().__init__()
        self.ser = porta_serial
        self._rodando = True

    def run(self):
        while self._rodando:
            try:
                bruto = self.ser.readline()
            except Exception as e:
                if self._rodando:
                    self.caiu.emit(str(e))
                return
            if bruto:
                texto = bruto.decode("utf-8", errors="replace").strip()
                if texto:
                    self.linha.emit(texto)

    def parar(self):
        self._rodando = False
        self.wait(800)


# ---------------------------------------------------------------- painel motor
class PainelMotor(QGroupBox):
    def __init__(self, titulo, preset_inicial):
        super().__init__(titulo)
        self.ser = None
        self.leitor = None
        self._pronto = False       # so envia config depois do reset do Arduino

        self._montar_ui(preset_inicial)
        self._conectar_sinais()
        self.aplicar_preset(preset_inicial)
        self._atualizar_conectado(False)

        self.timer_status = QTimer(self)
        self.timer_status.timeout.connect(self._pedir_status)
        self.timer_status.setInterval(300)

    # ------------------------------------------------------------------ UI
    def _montar_ui(self, preset_inicial):
        # --- conexao ---
        self.cb_porta = QComboBox()
        self.cb_porta.setMinimumWidth(150)
        self.bt_atualizar = QPushButton("Atualizar")
        self.cb_baud = QComboBox()
        self.cb_baud.addItems(BAUDS)
        self.bt_conectar = QPushButton("Conectar")
        self.bt_conectar.setCheckable(True)

        lin_conn = QHBoxLayout()
        lin_conn.addWidget(QLabel("Porta:"))
        lin_conn.addWidget(self.cb_porta, 1)
        lin_conn.addWidget(self.bt_atualizar)
        lin_conn.addWidget(QLabel("Baud:"))
        lin_conn.addWidget(self.cb_baud)
        lin_conn.addWidget(self.bt_conectar)

        # --- driver / mecanica ---
        self.cb_driver = QComboBox()
        self.cb_driver.addItems(PRESETS.keys())
        self.cb_driver.setCurrentText(preset_inicial)

        self.cb_micro = QComboBox()
        self.sp_spr = QSpinBox()
        self.sp_spr.setRange(1, 10000)
        self.sp_spr.setValue(200)
        self.lb_ppr = QLabel("-")

        self.cb_enapol = QComboBox()
        self.cb_enapol.addItems(["LOW habilita (A4988)", "HIGH habilita (DM556)"])
        self.ck_invdir = QCheckBox("Inverter sentido do pino DIR")

        f_drv = QFormLayout()
        f_drv.addRow("Driver:", self.cb_driver)
        f_drv.addRow("Microstep (x):", self.cb_micro)
        f_drv.addRow("Passos inteiros/volta:", self.sp_spr)
        f_drv.addRow("Pulsos por volta:", self.lb_ppr)
        f_drv.addRow("ENABLE:", self.cb_enapol)
        f_drv.addRow("", self.ck_invdir)
        g_drv = QGroupBox("Driver")
        g_drv.setLayout(f_drv)

        # --- movimento ---
        self.sp_passos = QSpinBox()
        self.sp_passos.setRange(1, 2_000_000)
        self.sp_passos.setSingleStep(50)

        self.sp_vel = QSpinBox()
        self.sp_vel.setRange(1, 40000)
        self.sp_vel.setSingleStep(50)
        self.sp_vel.setSuffix(" passos/s")

        self.sp_veli = QSpinBox()
        self.sp_veli.setRange(1, 40000)
        self.sp_veli.setSingleStep(50)
        self.sp_veli.setSuffix(" passos/s")

        self.sp_acel = QSpinBox()
        self.sp_acel.setRange(0, 400000)
        self.sp_acel.setSingleStep(500)
        self.sp_acel.setSuffix(" passos/s²")

        self.sp_pausa = QSpinBox()
        self.sp_pausa.setRange(0, 600000)
        self.sp_pausa.setSingleStep(50)
        self.sp_pausa.setSuffix(" ms")
        self.sp_pausa.setValue(500)

        self.sp_rep = QSpinBox()
        self.sp_rep.setRange(0, 1_000_000)
        self.sp_rep.setValue(0)
        self.sp_rep.setSpecialValueText("infinito")

        self.cb_dir = QComboBox()
        self.cb_dir.addItems(["Horário (DIR=1)", "Anti-horário (DIR=0)"])
        self.ck_alterna = QCheckBox("Alternar direção a cada movimento")

        self.lb_graus = QLabel("-")
        self.lb_rpm = QLabel("-")

        f_mov = QFormLayout()
        f_mov.addRow("Passos por movimento:", self.sp_passos)
        f_mov.addRow("Velocidade:", self.sp_vel)
        f_mov.addRow("Velocidade inicial:", self.sp_veli)
        f_mov.addRow("Aceleração (0 = sem rampa):", self.sp_acel)
        f_mov.addRow("Pausa entre movimentos:", self.sp_pausa)
        f_mov.addRow("Repetições:", self.sp_rep)
        f_mov.addRow("Direção:", self.cb_dir)
        f_mov.addRow("", self.ck_alterna)
        f_mov.addRow("Giro por movimento:", self.lb_graus)
        f_mov.addRow("Rotação:", self.lb_rpm)
        g_mov = QGroupBox("Movimento")
        g_mov.setLayout(f_mov)

        # --- comandos ---
        self.bt_habilitar = QPushButton("Habilitar")
        self.bt_habilitar.setCheckable(True)
        self.bt_iniciar = QPushButton("Iniciar")
        self.bt_parar = QPushButton("Parar")
        self.bt_mover_h = QPushButton("Mover 1x  ⟳")
        self.bt_mover_a = QPushButton("Mover 1x  ⟲")
        self.bt_zerar = QPushButton("Zerar posição")
        self.bt_reenviar = QPushButton("Reenviar config")

        g_cmd = QGridLayout()
        g_cmd.addWidget(self.bt_habilitar, 0, 0)
        g_cmd.addWidget(self.bt_iniciar, 0, 1)
        g_cmd.addWidget(self.bt_parar, 0, 2)
        g_cmd.addWidget(self.bt_mover_a, 1, 0)
        g_cmd.addWidget(self.bt_mover_h, 1, 1)
        g_cmd.addWidget(self.bt_zerar, 1, 2)
        g_cmd.addWidget(self.bt_reenviar, 2, 0, 1, 3)
        cx_cmd = QGroupBox("Comandos")
        cx_cmd.setLayout(g_cmd)

        # --- status e log ---
        self.lb_status = QLabel("desconectado")
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)
        self.log.setStyleSheet("font-family: monospace; font-size: 11px;")

        v = QVBoxLayout(self)
        v.addLayout(lin_conn)
        v.addWidget(g_drv)
        v.addWidget(g_mov)
        v.addWidget(cx_cmd)
        v.addWidget(self.lb_status)
        v.addWidget(self.log, 1)

        self.listar_portas()

    def _conectar_sinais(self):
        self.bt_atualizar.clicked.connect(self.listar_portas)
        self.bt_conectar.clicked.connect(self._alternar_conexao)
        self.cb_driver.currentTextChanged.connect(self.aplicar_preset)

        for w in (self.cb_micro, self.cb_enapol, self.cb_dir):
            w.currentIndexChanged.connect(self._config_mudou)
        for w in (self.sp_spr, self.sp_passos, self.sp_vel, self.sp_veli,
                  self.sp_acel, self.sp_pausa, self.sp_rep):
            w.valueChanged.connect(self._config_mudou)
        for w in (self.ck_invdir, self.ck_alterna):
            w.stateChanged.connect(self._config_mudou)

        self.bt_habilitar.clicked.connect(
            lambda: self.enviar(f"EN {1 if self.bt_habilitar.isChecked() else 0}"))
        self.bt_iniciar.clicked.connect(self._iniciar)
        self.bt_parar.clicked.connect(lambda: self.enviar("STOP"))
        self.bt_zerar.clicked.connect(lambda: self.enviar("ZERO"))
        self.bt_reenviar.clicked.connect(self.enviar_config)
        self.bt_mover_h.clicked.connect(
            lambda: self.enviar(f"MOVE {self.sp_passos.value()} 1"))
        self.bt_mover_a.clicked.connect(
            lambda: self.enviar(f"MOVE {self.sp_passos.value()} 0"))

    # --------------------------------------------------------------- presets
    def aplicar_preset(self, nome):
        p = PRESETS[nome]
        self.cb_micro.blockSignals(True)
        self.cb_micro.clear()
        self.cb_micro.addItems([str(m) for m in p["micros"]])
        self.cb_micro.setCurrentText(str(p["micro"]))
        self.cb_micro.blockSignals(False)

        for w, val in ((self.cb_enapol, p["enapol"]),):
            w.blockSignals(True)
            w.setCurrentIndex(val)
            w.blockSignals(False)
        for w, val in ((self.sp_vel, p["vel"]), (self.sp_veli, p["veli"]),
                       (self.sp_acel, p["acel"]), (self.sp_passos, p["passos"])):
            w.blockSignals(True)
            w.setValue(val)
            w.blockSignals(False)

        self._config_mudou()

    # ---------------------------------------------------------------- conexao
    def listar_portas(self):
        atual = self.cb_porta.currentText()
        self.cb_porta.clear()
        for p in serial.tools.list_ports.comports():
            self.cb_porta.addItem(p.device, p.device)
        if atual:
            i = self.cb_porta.findText(atual)
            if i >= 0:
                self.cb_porta.setCurrentIndex(i)

    def _alternar_conexao(self):
        if self.bt_conectar.isChecked():
            self.conectar()
        else:
            self.desconectar()

    def conectar(self):
        porta = self.cb_porta.currentText()
        if not porta:
            self.escrever("nenhuma porta selecionada")
            self.bt_conectar.setChecked(False)
            return
        try:
            self.ser = serial.Serial(porta, int(self.cb_baud.currentText()),
                                     timeout=0.2)
        except Exception as e:
            self.escrever(f"falha ao abrir {porta}: {e}")
            self.bt_conectar.setChecked(False)
            return

        self.leitor = Leitor(self.ser)
        self.leitor.linha.connect(self._recebeu)
        self.leitor.caiu.connect(self._erro_serial)
        self.leitor.start()

        self._atualizar_conectado(True)
        self.escrever(f"conectado em {porta}")
        # o Arduino reinicia ao abrir a porta: espera antes de configurar
        QTimer.singleShot(2000, self._apos_reset)

    def _apos_reset(self):
        if not self.ser:
            return
        self._pronto = True
        self.enviar("ID")
        self.enviar_config()
        self.timer_status.start()

    def desconectar(self):
        self.timer_status.stop()
        self._pronto = False
        if self.ser:
            try:
                self.ser.write(b"STOP\nEN 0\n")
                time.sleep(0.05)
            except Exception:
                pass
        if self.leitor:
            self.leitor.parar()
            self.leitor = None
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
        self._atualizar_conectado(False)
        self.escrever("desconectado")

    def _erro_serial(self, msg):
        self.escrever(f"erro na serial: {msg}")
        self.bt_conectar.setChecked(False)
        self.desconectar()

    def _atualizar_conectado(self, ok):
        self.bt_conectar.setText("Desconectar" if ok else "Conectar")
        self.bt_conectar.setChecked(ok)
        self.cb_porta.setEnabled(not ok)
        self.cb_baud.setEnabled(not ok)
        self.bt_atualizar.setEnabled(not ok)
        for b in (self.bt_habilitar, self.bt_iniciar, self.bt_parar,
                  self.bt_mover_h, self.bt_mover_a, self.bt_zerar,
                  self.bt_reenviar):
            b.setEnabled(ok)
        if not ok:
            self.bt_habilitar.setChecked(False)
            self.lb_status.setText("desconectado")

    # ------------------------------------------------------------ comunicacao
    def enviar(self, linha):
        if not self.ser:
            return
        try:
            self.ser.write((linha + "\n").encode())
        except Exception as e:
            self._erro_serial(str(e))
            return
        if not linha.startswith("ST"):
            self.escrever("> " + linha)

    def enviar_config(self):
        if not self._pronto:
            return
        for chave, valor in self._config().items():
            self.enviar(f"CFG {chave} {valor}")

    def _config(self):
        return {
            "MICRO": self.cb_micro.currentText() or "1",
            "SPR": self.sp_spr.value(),
            "VEL": self.sp_vel.value(),
            "VELI": min(self.sp_veli.value(), self.sp_vel.value()),
            "ACC": self.sp_acel.value(),
            "PASSOS": self.sp_passos.value(),
            "PAUSA": self.sp_pausa.value(),
            "REP": self.sp_rep.value(),
            "DIR": 1 if self.cb_dir.currentIndex() == 0 else 0,
            "INVDIR": 1 if self.ck_invdir.isChecked() else 0,
            "ENAPOL": self.cb_enapol.currentIndex(),
            "ALT": 1 if self.ck_alterna.isChecked() else 0,
        }

    def _config_mudou(self):
        micro = int(self.cb_micro.currentText() or 1)
        ppr = self.sp_spr.value() * micro
        self.lb_ppr.setText(f"{ppr}")
        self.lb_graus.setText(f"{self.sp_passos.value() / ppr * 360:.2f}°")
        self.lb_rpm.setText(f"{self.sp_vel.value() / ppr * 60:.1f} rpm")
        self.enviar_config()

    def _iniciar(self):
        self.enviar_config()
        self.bt_habilitar.setChecked(True)
        self.enviar("START")

    def _pedir_status(self):
        self.enviar("ST")

    def _recebeu(self, linha):
        if linha.startswith("ST "):
            self._ler_status(linha)
        else:
            self.escrever("< " + linha)
            if linha.startswith("EV PRONTO"):
                self.enviar_config()

    def _ler_status(self, linha):
        d = {}
        for parte in linha.split()[1:]:
            if "=" in parte:
                k, v = parte.split("=", 1)
                d[k] = v
        est = ESTADOS.get(d.get("est", ""), "?")
        hab = "ligado" if d.get("en") == "1" else "desligado"
        self.bt_habilitar.blockSignals(True)
        self.bt_habilitar.setChecked(d.get("en") == "1")
        self.bt_habilitar.blockSignals(False)
        self.bt_habilitar.setText("Desabilitar" if d.get("en") == "1" else "Habilitar")
        self.lb_status.setText(
            f"{est} | driver {hab} | pos {d.get('pos','-')} | "
            f"faltam {d.get('rest','-')} | movs {d.get('mov','-')} | "
            f"{d.get('vel','-')} passos/s"
        )

    def escrever(self, txt):
        self.log.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {txt}")

    def encerrar(self):
        self.desconectar()


# ---------------------------------------------------------------- janela
class Janela(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Controle de motores de passo")
        self.resize(1180, 820)

        self.esq = PainelMotor("Motor 1 — NEMA 17 / A4988", "A4988 / NEMA 17")
        self.dir = PainelMotor("Motor 2 — NEMA 23 / DM556", "DM556 / NEMA 23")

        divisor = QFrame()
        divisor.setFrameShape(QFrame.Shape.VLine)
        divisor.setFrameShadow(QFrame.Shadow.Sunken)

        topo = QHBoxLayout()
        topo.addWidget(self.esq, 1)
        topo.addWidget(divisor)
        topo.addWidget(self.dir, 1)

        self.bt_emergencia = QPushButton("PARAR TUDO")
        self.bt_emergencia.setMinimumHeight(42)
        self.bt_emergencia.setStyleSheet("font-weight: bold;")
        self.bt_emergencia.clicked.connect(self.parar_tudo)

        v = QVBoxLayout(self)
        v.addLayout(topo, 1)
        v.addWidget(self.bt_emergencia)

    def parar_tudo(self):
        for p in (self.esq, self.dir):
            p.enviar("STOP")
            p.enviar("EN 0")

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.parar_tudo()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        self.parar_tudo()
        self.esq.encerrar()
        self.dir.encerrar()
        e.accept()


def main():
    app = QApplication(sys.argv)
    j = Janela()
    j.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
