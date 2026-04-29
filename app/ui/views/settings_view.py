"""Vista de configuración: proveedor de IA, API key, Whisper y rutas."""
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QRadioButton, QButtonGroup, QComboBox, QPushButton,
    QFileDialog, QScrollArea, QFrame,
)

from app.config import AI_PROVIDERS, CONFIG_PATH, OUTPUTS_DIR
from app.core.ai_client import build_ai_client
from app.ui.components.card_widget import CardWidget
from app.ui.components.icon_button import IconButton
from app.ui.components.toast_manager import ToastManager
from app.ui.svg_helper import svg_icon
from app.ui.tokens import (
    COLOR_BG_SURFACE, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_SUCCESS, COLOR_ERROR, SPACE_LG,
)
from app.utils.secrets import AIConfig, SecretsManager


class _ValidateWorker(QThread):
    """Valida la API key en un hilo separado."""
    result = pyqtSignal(bool, str)

    def __init__(self, config: AIConfig) -> None:
        super().__init__()
        self._config = config

    def run(self) -> None:
        try:
            client = build_ai_client(self._config)
            ok = client.validate_key()
            self.result.emit(ok, "" if ok else "La key no es válida")
        except Exception as exc:
            self.result.emit(False, str(exc))


class SettingsView(QWidget):
    """Vista de configuración de la aplicación."""

    config_saved = pyqtSignal(AIConfig)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._secrets = SecretsManager(CONFIG_PATH)
        self._validate_worker: _ValidateWorker | None = None
        self._key_validated = False
        self._setup_ui()
        self._load_saved_config()

    def _setup_ui(self) -> None:
        self.setObjectName("settingsView")
        self.setStyleSheet(f"#settingsView {{ background: {COLOR_BG_SURFACE}; }}")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(SPACE_LG, SPACE_LG, SPACE_LG, SPACE_LG)
        main_layout.setSpacing(SPACE_LG)

        title = QLabel("Configuración")
        title.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 18px; font-weight: 600;")
        main_layout.addWidget(title)

        main_layout.addWidget(self._build_provider_card())
        main_layout.addWidget(self._build_whisper_card())
        main_layout.addWidget(self._build_paths_card())
        main_layout.addStretch()

        # Botón guardar
        save_row = QHBoxLayout()
        save_row.addStretch()
        self._save_btn = IconButton("action_export", "  Guardar configuración", "primary")
        self._save_btn.setFixedHeight(44)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_config)
        save_row.addWidget(self._save_btn)
        main_layout.addLayout(save_row)

        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        # Seleccionar primer proveedor después de que _save_btn ya existe
        list(self._provider_radios.values())[0].setChecked(True)

    def _build_provider_card(self) -> QWidget:
        card = CardWidget("Proveedor de IA")
        layout = card.layout()

        # Radio buttons de proveedor
        self._provider_group = QButtonGroup(self)
        self._provider_radios: dict[str, QRadioButton] = {}

        for key, info in AI_PROVIDERS.items():
            radio = QRadioButton(info["name"])
            radio.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-size: 13px;")
            radio.toggled.connect(lambda checked, k=key: self._on_provider_changed(k) if checked else None)
            self._provider_group.addButton(radio)
            self._provider_radios[key] = radio
            layout.addWidget(radio)

        # API Key
        key_label = QLabel("API Key")
        key_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; margin-top: 8px;")
        layout.addWidget(key_label)

        key_row = QHBoxLayout()
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("Ingresa tu API key...")
        self._key_input.textChanged.connect(self._on_key_changed)

        self._eye_btn = QPushButton()
        self._eye_btn.setFixedSize(36, 36)
        self._eye_btn.setCheckable(True)
        self._eye_btn.setStyleSheet("QPushButton { background: #2D3748; border-radius: 6px; border: 1px solid #4A5568; } QPushButton:checked { border-color: #F97316; }")
        self._eye_btn.setIcon(svg_icon("eye_off", 18, COLOR_TEXT_SECONDARY))
        self._eye_btn.setIconSize(QSize(18, 18))
        self._eye_btn.toggled.connect(self._toggle_key_visibility)

        self._validate_btn = IconButton("status_check", "  Validar", "secondary")
        self._validate_btn.setFixedHeight(36)
        self._validate_btn.clicked.connect(self._validate_key)

        key_row.addWidget(self._key_input)
        key_row.addWidget(self._eye_btn)
        key_row.addWidget(self._validate_btn)
        layout.addLayout(key_row)

        self._key_status = QLabel("")
        self._key_status.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(self._key_status)

        # Modelo
        model_label = QLabel("Modelo")
        model_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; margin-top: 8px;")
        layout.addWidget(model_label)

        self._model_combo = QComboBox()
        layout.addWidget(self._model_combo)

        return card

    def _build_whisper_card(self) -> QWidget:
        card = CardWidget("Configuración de Whisper")
        layout = card.layout()

        lang_label = QLabel("Idioma")
        lang_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(lang_label)

        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["es — Español", "en — Inglés", "auto — Detección automática"])
        layout.addWidget(self._lang_combo)

        device_label = QLabel("Dispositivo de procesamiento")
        device_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px; margin-top: 8px;")
        layout.addWidget(device_label)

        self._device_combo = QComboBox()
        self._device_combo.addItems(["auto — Automático (recomendado)", "cpu — CPU", "cuda — GPU (NVIDIA)"])
        layout.addWidget(self._device_combo)

        try:
            import torch
            if torch.cuda.is_available():
                gpu_info = QLabel(f"GPU detectada: {torch.cuda.get_device_name(0)}")
                gpu_info.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 11px;")
                layout.addWidget(gpu_info)
        except Exception:
            pass

        return card

    def _build_paths_card(self) -> QWidget:
        card = CardWidget("Rutas de salida")
        layout = card.layout()

        path_label = QLabel("Directorio de proyectos")
        path_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 12px;")
        layout.addWidget(path_label)

        path_row = QHBoxLayout()
        self._output_path_input = QLineEdit(str(OUTPUTS_DIR))
        self._output_path_input.setReadOnly(True)

        browse_btn = IconButton("action_open_folder", "", "ghost")
        browse_btn.setFixedSize(36, 36)
        browse_btn.clicked.connect(self._browse_output_dir)

        path_row.addWidget(self._output_path_input)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        return card

    def _on_provider_changed(self, key: str) -> None:
        models = AI_PROVIDERS.get(key, {}).get("models", [])
        self._model_combo.clear()
        self._model_combo.addItems(models)
        default = AI_PROVIDERS.get(key, {}).get("default_model", "")
        idx = self._model_combo.findText(default)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        self._key_validated = False
        self._save_btn.setEnabled(False)
        self._key_status.setText("")

    def _on_key_changed(self, _text: str) -> None:
        self._key_validated = False
        self._save_btn.setEnabled(False)
        self._key_status.setText("")

    def _toggle_key_visibility(self, visible: bool) -> None:
        self._key_input.setEchoMode(QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)
        icon_name = "eye" if visible else "eye_off"
        self._eye_btn.setIcon(svg_icon(icon_name, 18, COLOR_TEXT_SECONDARY))

    def _validate_key(self) -> None:
        key = self._key_input.text().strip()
        if not key:
            ToastManager.instance().warning("Ingresa una API key primero")
            return

        provider = self._get_selected_provider()
        model = self._model_combo.currentText()

        self._validate_btn.setEnabled(False)
        self._key_status.setText("Validando...")
        self._key_status.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY}; font-size: 11px;")

        config = AIConfig(provider=provider, api_key=key, model=model)
        self._validate_worker = _ValidateWorker(config)
        self._validate_worker.result.connect(self._on_validate_result)
        self._validate_worker.start()

    def _on_validate_result(self, ok: bool, message: str) -> None:
        self._validate_btn.setEnabled(True)
        if ok:
            self._key_validated = True
            self._save_btn.setEnabled(True)
            self._key_status.setText("Key válida")
            self._key_status.setStyleSheet(f"color: {COLOR_SUCCESS}; font-size: 11px;")
            ToastManager.instance().success("API key validada correctamente")
        else:
            self._key_validated = False
            self._save_btn.setEnabled(False)
            self._key_status.setText(f"Key inválida: {message}")
            self._key_status.setStyleSheet(f"color: {COLOR_ERROR}; font-size: 11px;")
            ToastManager.instance().error(f"API key inválida: {message}")

    def _save_config(self) -> None:
        if not self._key_validated:
            ToastManager.instance().warning("Valida la API key antes de guardar")
            return

        config = AIConfig(
            provider=self._get_selected_provider(),
            api_key=self._key_input.text().strip(),
            model=self._model_combo.currentText(),
        )
        self._secrets.save_ai_config(config)
        self.config_saved.emit(config)
        ToastManager.instance().success("Configuración guardada correctamente")

    def _get_selected_provider(self) -> str:
        for key, radio in self._provider_radios.items():
            if radio.isChecked():
                return key
        return "gemini"

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Seleccionar directorio de salida")
        if path:
            self._output_path_input.setText(path)

    def _load_saved_config(self) -> None:
        config = self._secrets.load_ai_config()
        if config:
            radio = self._provider_radios.get(config.provider)
            if radio:
                radio.setChecked(True)
            self._key_input.setText(config.api_key)
            idx = self._model_combo.findText(config.model)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)

    def get_current_config(self) -> AIConfig | None:
        """Retorna la configuración actual guardada."""
        return self._secrets.load_ai_config()
