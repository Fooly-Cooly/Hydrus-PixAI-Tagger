import sys
import json
import os
import hashlib
import time
import subprocess


def _ensure_runtime_environment():
    """Ensure the script runs inside the project virtual environment with safe GUI streams."""
    # 1. Sanitize standard streams for pythonw (sys.stdout and sys.stderr are None in pythonw on Windows)
    is_gui_runner = (
        sys.platform == "win32"
        and ("pythonw" in os.path.basename(sys.executable).lower() or sys.stdout is None)
    )

    if sys.stdout is None:
        try:
            sys.stdout = open(os.devnull, "w", encoding="utf-8")
        except Exception:
            pass
    if sys.stderr is None:
        try:
            sys.stderr = open(os.devnull, "w", encoding="utf-8")
        except Exception:
            pass

    project_root = os.path.dirname(os.path.abspath(__file__))

    # 2. Install GUI crash handler for headless/no-console execution
    def _excepthook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, SystemExit):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        import traceback
        import datetime
        tb_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        crash_log = os.path.join(project_root, "crash.log")
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(crash_log, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*25} Crash at {timestamp} {'='*25}\n")
                f.write(tb_text)
                f.write("\n")
        except Exception:
            pass

        if sys.platform == "win32":
            try:
                import ctypes
                preview = tb_text if len(tb_text) < 1000 else tb_text[:1000] + "\n\n... (Full traceback saved to crash.log)"
                ctypes.windll.user32.MessageBoxW(
                    0,
                    f"An unexpected error occurred in Hydrus PixAI Tagger:\n\n{preview}",
                    "Hydrus PixAI Tagger - Error",
                    0x10  # MB_ICONERROR
                )
                return
            except Exception:
                pass
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = _excepthook

    # 3. Prevent infinite relaunch loops
    if os.environ.get("_HYDRUS_TAGGER_RELAUNCHED") == "1":
        return

    def show_error(title, message):
        if is_gui_runner and sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)  # MB_ICONERROR
                return
            except Exception:
                pass
        sys.stderr.write(f"[{title}] {message}\n")

    # 3. Locate virtual environment python executable
    candidates = []
    if sys.platform == "win32":
        names = ["pythonw.exe", "python.exe"] if is_gui_runner else ["python.exe", "pythonw.exe"]
        for venv_dir in ["venv", ".venv"]:
            for name in names:
                candidates.append(os.path.join(project_root, venv_dir, "Scripts", name))
                candidates.append(os.path.join(project_root, venv_dir, name))
    else:
        for venv_dir in ["venv", ".venv"]:
            candidates.append(os.path.join(project_root, venv_dir, "bin", "python3"))
            candidates.append(os.path.join(project_root, venv_dir, "bin", "python"))

    target_venv_python = None
    for cand in candidates:
        if os.path.isfile(cand):
            target_venv_python = cand
            break

    # 4. Check if current interpreter is already running inside the target venv
    def is_in_target_venv(target_python):
        # The virtual environment root directory is the parent of Scripts/ (Windows) or bin/ (POSIX)
        target_venv_dir = os.path.dirname(os.path.dirname(os.path.abspath(target_python)))
        try:
            return os.path.samefile(sys.prefix, target_venv_dir)
        except Exception:
            return os.path.normcase(os.path.abspath(sys.prefix)) == os.path.normcase(os.path.abspath(target_venv_dir))

    if target_venv_python:
        in_target_venv = is_in_target_venv(target_venv_python)

        # On Windows, also verify runner type (pythonw.exe vs python.exe)
        needs_relaunch = not in_target_venv
        if in_target_venv and sys.platform == "win32" and is_gui_runner:
            if "pythonw" not in os.path.basename(sys.executable).lower():
                needs_relaunch = True

        if needs_relaunch:
            env = os.environ.copy()
            env["_HYDRUS_TAGGER_RELAUNCHED"] = "1"
            cmd = [target_venv_python, os.path.abspath(__file__)] + sys.argv[1:]

            if is_gui_runner and sys.platform == "win32":
                # Launch detached without a console window on Windows
                DETACHED_PROCESS = 0x00000008
                CREATE_NO_WINDOW = 0x08000000
                subprocess.Popen(
                    cmd,
                    cwd=project_root,
                    env=env,
                    creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
                    close_fds=True,
                )
                sys.exit(0)
            elif sys.platform != "win32":
                # On Linux/macOS, replace the current process in place
                try:
                    os.execve(target_venv_python, cmd, env)
                except Exception:
                    result = subprocess.call(cmd, cwd=project_root, env=env)
                    sys.exit(result)
            else:
                # Synchronous console execution on Windows, forward exit code
                result = subprocess.call(cmd, cwd=project_root, env=env)
                sys.exit(result)
    else:
        # No venv found; verify if current interpreter has required dependencies
        try:
            import PyQt6  # noqa: F401
            import torch  # noqa: F401
            import transformers  # noqa: F401
            import hydrus_api  # noqa: F401
        except ImportError:
            setup_cmd = "setup.bat" if sys.platform == "win32" else "./setup.sh"
            show_error(
                "Hydrus PixAI Tagger - Setup Required",
                f"Virtual environment not found and required dependencies are missing.\n\n"
                f"Please run '{setup_cmd}' first to install the virtual environment "
                f"and dependencies before launching.",
            )
            sys.exit(1)


_ensure_runtime_environment()

# Force Hugging Face cache to live inside the local project folder
os.environ["HF_HOME"] = os.path.join(os.path.dirname(__file__), "hf_cache")

# Import lightweight GUI modules immediately so the startup UI renders in milliseconds
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QLineEdit, QDoubleSpinBox,
    QTextEdit, QMessageBox, QProgressBar, QCheckBox, QGroupBox
)

# Placeholders for heavy AI and network dependencies loaded with the splash screen
torch = None
Image = None
pipeline = None
hydrus_api = None


def _load_ai_dependencies():
    """Load PyTorch, Transformers, Pillow, and Hydrus API with status visibility."""
    global torch, Image, pipeline, hydrus_api
    if torch is None:
        import torch as _torch
        torch = _torch
    if pipeline is None:
        from transformers import pipeline as _pipeline
        pipeline = _pipeline
    if Image is None:
        from PIL import Image as _Image
        Image = _Image
    if hydrus_api is None:
        import hydrus_api as _hydrus_api
        hydrus_api = _hydrus_api

VALID_IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff", ".tif", ".avif"
}


def calculate_sha256(file_path: str) -> str:
    """Calculate the SHA256 hash of a local file as required by Hydrus Network."""
    if hasattr(hashlib, "file_digest"):
        with open(file_path, "rb") as f:
            return hashlib.file_digest(f, "sha256").hexdigest()
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class TaggerThread(QThread):
    """Background thread to handle model inference and Hydrus API operations."""
    log_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int, int)
    finished_signal = pyqtSignal()
    pipeline_loaded_signal = pyqtSignal(object, tuple)

    RECOMMENDED_THRESHOLDS = {
        "general": 0.17,
        "character": 0.27,
        "style": 0.15,
        "copyright": 0.24,
        "meta": 0.17,
        "rating": 0.41,
        "artist": 0.24
    }

    NAMESPACE_MAP = {
        "character": "character",
        "copyright": "series",
        "artist": "creator",
        "meta": "meta",
        "rating": "rating",
        "style": "style"
    }

    def __init__(self, file_paths, api_url, api_key, service_name, threshold_config, 
                 device_setting, use_namespaces, use_fp16, batch_size, 
                 enabled_categories, blacklisted_tags, 
                 cached_pipeline=None, cached_pipeline_config=None, parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.api_url = api_url
        self.api_key = api_key
        self.service_name = service_name
        self.threshold_config = threshold_config
        self.device_setting = device_setting
        self.use_namespaces = use_namespaces
        self.use_fp16 = use_fp16
        self.batch_size = max(1, batch_size)
        self.enabled_categories = enabled_categories
        self.blacklisted_tags = {t.strip().lower() for t in blacklisted_tags if t.strip()}
        self.cached_pipeline = cached_pipeline
        self.cached_pipeline_config = cached_pipeline_config
        self.tagger = None

    def _find_key_in_data(self, data, target_name):
        """Recursively searches the Hydrus API services payload for the matching service key."""
        if isinstance(data, dict):
            if "name" in data and "service_key" in data:
                if str(data["name"]).strip().lower() == target_name:
                    return data["service_key"]
            for k, v in data.items():
                if isinstance(v, dict) and str(v.get("name", "")).strip().lower() == target_name:
                    return v.get("service_key", k)
                res = self._find_key_in_data(v, target_name)
                if res:
                    return res
        elif isinstance(data, list):
            for item in data:
                res = self._find_key_in_data(item, target_name)
                if res:
                    return res
        return None

    def run(self):
        start_time = time.time()
        try:
            # 1. Device and precision determination
            cuda_available = torch.cuda.is_available()
            if self.device_setting == "CUDA (GPU)":
                if cuda_available:
                    device = 0
                    gpu_name = torch.cuda.get_device_name(0)
                    self.log_signal.emit(f"Running pipeline on GPU: {gpu_name}")
                else:
                    device = -1
                    self.log_signal.emit("CUDA requested but not available. Falling back to CPU.")
            elif self.device_setting == "Auto" and cuda_available:
                device = 0
                gpu_name = torch.cuda.get_device_name(0)
                self.log_signal.emit(f"Running pipeline on GPU: {gpu_name}")
            else:
                device = -1
                self.log_signal.emit("Running pipeline on CPU.")

            torch_dtype = torch.float16 if (device == 0 and self.use_fp16) else torch.float32
            self.log_signal.emit(f"Precision: {'FP16 (Half Precision)' if torch_dtype == torch.float16 else 'FP32 (Standard)'}")

            # 2. Load or reuse Model Pipeline
            current_config = (device, torch_dtype)
            if self.cached_pipeline is not None and self.cached_pipeline_config == current_config:
                self.tagger = self.cached_pipeline
                self.log_signal.emit("Reusing loaded PixAI Tagger model.")
            else:
                self.log_signal.emit("Loading PixAI Tagger model into memory...")
                try:
                    model_id = "pixai-labs/pixai-tagger-v1.0"
                    self.tagger = pipeline(
                        model=model_id,
                        image_processor=model_id,
                        trust_remote_code=True,
                        device=device,
                        torch_dtype=torch_dtype
                    )
                    self.pipeline_loaded_signal.emit(self.tagger, current_config)
                    self.log_signal.emit("Model loaded successfully.")
                except Exception as e:
                    self.log_signal.emit(f"Error loading model: {str(e)}")
                    return

            # 3. Connect to Hydrus API
            try:
                client = hydrus_api.Client(access_key=self.api_key, api_url=self.api_url)
                api_version = client.get_api_version()
                self.log_signal.emit(f"Connected to Hydrus API (v{api_version.get('version', 'unknown')}).")

                target_name = self.service_name.strip().lower()
                if len(target_name) == 64 and all(c in "0123456789abcdef" for c in target_name):
                    service_key = target_name
                    self.log_signal.emit("Service name looks like a raw Hex key. Using directly.")
                else:
                    services_data = client.get_services()
                    service_key = self._find_key_in_data(services_data, target_name)

                    if not service_key:
                        self.log_signal.emit(f"ERROR: Could not find tag service '{self.service_name}'.")
                        return

                    self.log_signal.emit(f"Resolved service '{self.service_name}' -> hex key '{service_key[:12]}...'")

            except Exception as e:
                self.log_signal.emit(f"Hydrus connection error: {str(e)}")
                return

            # 4. Batch Processing
            total_files = len(self.file_paths)
            processed_count = 0

            for i in range(0, total_files, self.batch_size):
                if self.isInterruptionRequested():
                    self.log_signal.emit("Tagging operation interrupted by user.")
                    break

                chunk_paths = self.file_paths[i:i + self.batch_size]

                valid_entries = []
                for path in chunk_paths:
                    if not os.path.exists(path):
                        self.log_signal.emit(f"File not found: {path}")
                        continue
                    try:
                        img = Image.open(path).convert("RGB")
                        valid_entries.append((path, img))
                    except Exception as e:
                        self.log_signal.emit(f"Error reading {os.path.basename(path)}: {str(e)}")

                if not valid_entries:
                    processed_count += len(chunk_paths)
                    self.progress_signal.emit(processed_count, total_files)
                    continue

                valid_paths = [e[0] for e in valid_entries]
                valid_images = [e[1] for e in valid_entries]

                self.log_signal.emit(f"\nProcessing batch of {len(valid_images)} image(s)...")

                try:
                    with torch.inference_mode():
                        if len(valid_images) == 1:
                            res = self.tagger(valid_images[0], threshold=self.threshold_config)
                            pipe_outputs = [res] if isinstance(res, dict) else res
                        else:
                            pipe_outputs = self.tagger(
                                valid_images,
                                threshold=self.threshold_config,
                                batch_size=len(valid_images)
                            )
                            if isinstance(pipe_outputs, dict):
                                pipe_outputs = [pipe_outputs]

                except Exception as e:
                    self.log_signal.emit(f"Inference error on batch: {str(e)}")
                    processed_count += len(chunk_paths)
                    self.progress_signal.emit(processed_count, total_files)
                    continue
                finally:
                    for img in valid_images:
                        try:
                            img.close()
                        except Exception:
                            pass

                # Guard: verify 1-to-1 output alignment to guarantee zero tag-to-image mismatching
                if len(pipe_outputs) != len(valid_paths):
                    self.log_signal.emit(
                        f"ERROR: Output count mismatch (expected {len(valid_paths)}, got {len(pipe_outputs)}). "
                        "Skipping batch to prevent tag-to-image mismatching."
                    )
                    processed_count += len(chunk_paths)
                    self.progress_signal.emit(processed_count, total_files)
                    continue

                # 5. Process & Submit Tags
                for file_path, pipe_output in zip(valid_paths, pipe_outputs):
                    try:
                        file_hash = calculate_sha256(file_path)
                        results = pipe_output.get("results", {}) if isinstance(pipe_output, dict) else {}

                        filtered_tags = []
                        seen_tags = set()
                        for category, category_tags in results.items():
                            if not self.enabled_categories.get(category, True):
                                continue

                            if isinstance(category_tags, dict):
                                namespace = self.NAMESPACE_MAP.get(category, "") if self.use_namespaces else ""

                                for tag in category_tags.keys():
                                    raw_tag = tag.replace("_", " ").strip()
                                    if not raw_tag:
                                        continue
                                    
                                    if category == "rating":
                                        clean_tag = tag.lower().replace("rating:", "").strip()
                                        rating_map = {
                                            "g": "general",
                                            "s": "safe",
                                            "q": "questionable",
                                            "e": "explicit"
                                        }
                                        rating_val = rating_map.get(clean_tag, clean_tag)
                                        formatted_tag = f"rating:{rating_val}" if self.use_namespaces else rating_val
                                    else:
                                        formatted_tag = f"{namespace}:{raw_tag}" if namespace else raw_tag

                                    tag_lower = formatted_tag.lower()
                                    if raw_tag.lower() in self.blacklisted_tags or tag_lower in self.blacklisted_tags:
                                        continue

                                    if tag_lower not in seen_tags:
                                        seen_tags.add(tag_lower)
                                        filtered_tags.append(formatted_tag)

                        if self.enabled_categories.get("meta", True):
                            meta_tag = "meta:ai tagged (pixai v1.0)" if self.use_namespaces else "ai tagged (pixai v1.0)"
                            if (
                                meta_tag.lower() not in self.blacklisted_tags
                                and "ai tagged (pixai v1.0)" not in self.blacklisted_tags
                                and meta_tag.lower() not in seen_tags
                            ):
                                seen_tags.add(meta_tag.lower())
                                filtered_tags.append(meta_tag)

                        if filtered_tags:
                            client.add_tags(
                                hashes=[file_hash],
                                service_keys_to_tags={service_key: filtered_tags}
                            )
                            self.log_signal.emit(f"[{os.path.basename(file_path)}] Tagged with {len(filtered_tags)} tags.")
                        else:
                            self.log_signal.emit(f"[{os.path.basename(file_path)}] No tags passed threshold or all blacklisted.")

                    except Exception as e:
                        self.log_signal.emit(f"Error tagging {os.path.basename(file_path)}: {str(e)}")

                processed_count += len(chunk_paths)
                self.progress_signal.emit(processed_count, total_files)

            elapsed = time.time() - start_time
            avg_per_img = elapsed / total_files if total_files > 0 else 0
            self.log_signal.emit(f"\nBatch tagging completed: {total_files} file(s) in {elapsed:.2f}s ({avg_per_img:.2f}s/img).")

        finally:
            self.finished_signal.emit()


class DropAreaWidget(QLabel):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setWordWrap(True)     # Prevents horizontal stretching 
        self.setMinimumHeight(100) # Prevents vertical bouncing
        self.setText("Drag and Drop Image Files or Folders Here")

        # color: palette(window-text) forces Qt to use the correct Light/Dark mode text color
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #7f8c8d;
                border-radius: 8px;
                padding: 14px;
                background-color: rgba(128, 128, 128, 30);
                color: palette(window-text);
                font-size: 13px;
                font-weight: bold;
            }
            QLabel:hover {
                border-color: #3b82f6;
                background-color: rgba(128, 128, 128, 50);
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        event.acceptProposedAction()
        file_paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path):
                if os.path.splitext(path)[1].lower() in VALID_IMAGE_EXTENSIONS:
                    file_paths.append(path)
            elif os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if os.path.splitext(file)[1].lower() in VALID_IMAGE_EXTENSIONS:
                            file_paths.append(os.path.join(root, file))
        if file_paths:
            # Deduplicate paths while preserving discovery order
            unique_paths = list(dict.fromkeys(file_paths))
            self.files_dropped.emit(unique_paths)


class MainWindow(QMainWindow):
    CATEGORY_LABELS = {
        "general": "General",
        "character": "Character",
        "style": "Style",
        "copyright": "Copyright",
        "artist": "Artist",
        "meta": "Meta",
        "rating": "Rating"
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hydrus Network - PixAI Tagger v1.0")
        
        # Load app icon if present in directory
        icon_png = os.path.join(os.path.dirname(__file__), "icon.png")
        icon_ico = os.path.join(os.path.dirname(__file__), "icon.ico")
        icon_hydrus = os.path.join(os.path.dirname(__file__), "hydrus.ico")
        if os.path.exists(icon_png):
            self.setWindowIcon(QIcon(icon_png))
        elif os.path.exists(icon_ico):
            self.setWindowIcon(QIcon(icon_ico))
        elif os.path.exists(icon_hydrus):
            self.setWindowIcon(QIcon(icon_hydrus))

        # Snug, fixed-ratio initial sizing
        self.resize(580, 680)
        self.setMinimumWidth(560)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        # Ensure dependencies are available
        _load_ai_dependencies()

        self.presets = {}
        self.config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tagger_presets.json")
        self.cat_checkboxes = {}
        self.thread = None
        self.cached_pipeline = None
        self.cached_pipeline_config = None
        
        self.init_ui()
        self.load_presets()

    def init_ui(self):
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Connection & Presets Group
        conn_group = QGroupBox("Hydrus Connection Presets")
        conn_layout = QVBoxLayout()
        conn_layout.setContentsMargins(8, 8, 8, 8)
        conn_layout.setSpacing(5)

        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setEditable(True)
        self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo, stretch=1)

        self.btn_save_preset = QPushButton("Save")
        self.btn_save_preset.clicked.connect(self.save_preset)
        preset_layout.addWidget(self.btn_save_preset)

        self.btn_delete_preset = QPushButton("Delete")
        self.btn_delete_preset.clicked.connect(self.delete_preset)
        preset_layout.addWidget(self.btn_delete_preset)
        conn_layout.addLayout(preset_layout)

        form_layout = QFormLayout()
        form_layout.setSpacing(5)
        
        self.txt_api_url = QLineEdit("http://127.0.0.1:45871/")
        form_layout.addRow("API URL:", self.txt_api_url)

        key_layout = QHBoxLayout()
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        key_layout.addWidget(self.txt_api_key)

        self.btn_test_conn = QPushButton("Test Connection")
        self.btn_test_conn.clicked.connect(self.test_connection)
        key_layout.addWidget(self.btn_test_conn)

        form_layout.addRow("API Key:", key_layout)

        self.txt_service_name = QLineEdit("my tags")
        form_layout.addRow("Tag Service:", self.txt_service_name)

        conn_layout.addLayout(form_layout)
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)

        # 2. Engine & Performance Options Group
        engine_group = QGroupBox("Engine Performance")
        engine_layout = QHBoxLayout()
        engine_layout.setContentsMargins(8, 8, 8, 8)
        engine_layout.setSpacing(6)
        
        engine_layout.addWidget(QLabel("Device:"))
        self.combo_device = QComboBox()
        self.combo_device.addItems(["Auto", "CUDA (GPU)", "CPU"])
        engine_layout.addWidget(self.combo_device)

        engine_layout.addWidget(QLabel("Batch Size:"))
        self.combo_batch_size = QComboBox()
        self.combo_batch_size.addItems(["1", "2", "4", "8", "16", "32"])
        self.combo_batch_size.setCurrentText("8")
        engine_layout.addWidget(self.combo_batch_size)

        self.chk_use_fp16 = QCheckBox("FP16 (GPU)")
        self.chk_use_fp16.setChecked(True)
        engine_layout.addWidget(self.chk_use_fp16)
        engine_layout.addStretch()

        engine_group.setLayout(engine_layout)
        layout.addWidget(engine_group)

        # 3. Tagging Rules & Thresholds Group
        rules_group = QGroupBox("Tagging Rules")
        rules_layout = QVBoxLayout()
        rules_layout.setContentsMargins(8, 8, 8, 8)
        rules_layout.setSpacing(5)

        top_rules_layout = QHBoxLayout()
        self.chk_use_namespaces = QCheckBox("Prepend Namespaces")
        self.chk_use_namespaces.setChecked(True)
        top_rules_layout.addWidget(self.chk_use_namespaces)

        self.chk_use_recommended = QCheckBox("Use Recommended Thresholds")
        self.chk_use_recommended.setChecked(True)
        self.chk_use_recommended.toggled.connect(self.toggle_threshold_mode)
        top_rules_layout.addWidget(self.chk_use_recommended)

        top_rules_layout.addWidget(QLabel("Override:"))
        self.spin_threshold = QDoubleSpinBox()
        self.spin_threshold.setRange(0.01, 1.0)
        self.spin_threshold.setSingleStep(0.05)
        self.spin_threshold.setValue(0.20)
        self.spin_threshold.setEnabled(False)
        top_rules_layout.addWidget(self.spin_threshold)
        rules_layout.addLayout(top_rules_layout)

        blacklist_form = QFormLayout()
        self.txt_blacklist = QLineEdit()
        self.txt_blacklist.setPlaceholderText("comma-separated (e.g. monochrome, simple background)")
        blacklist_form.addRow("Tag Blacklist:", self.txt_blacklist)
        rules_layout.addLayout(blacklist_form)

        rules_group.setLayout(rules_layout)
        layout.addWidget(rules_group)

        # 4. Included Categories Group
        cat_group = QGroupBox("Included Tag Categories")
        cat_grid = QGridLayout()
        cat_grid.setContentsMargins(8, 8, 8, 8)
        cat_grid.setHorizontalSpacing(12)
        cat_grid.setVerticalSpacing(4)
        
        row, col = 0, 0
        for cat_key, cat_name in self.CATEGORY_LABELS.items():
            cb = QCheckBox(cat_name)
            cb.setChecked(True)
            self.cat_checkboxes[cat_key] = cb
            cat_grid.addWidget(cb, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

        cat_group.setLayout(cat_grid)
        layout.addWidget(cat_group)

        # 5. File Drop Area
        self.drop_area = DropAreaWidget()
        self.drop_area.files_dropped.connect(self.process_files)
        layout.addWidget(self.drop_area)

        # 6. Progress & Compact Console Output
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("Console Log"))
        log_header.addStretch()
        self.btn_clear_log = QPushButton("Clear Log")
        log_header.addWidget(self.btn_clear_log)
        layout.addLayout(log_header)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFixedHeight(130)  # Prevents layout inflation
        self.btn_clear_log.clicked.connect(self.log_output.clear)
        layout.addWidget(self.log_output)

        self.setCentralWidget(main_widget)

    def toggle_threshold_mode(self, use_recommended):
        self.spin_threshold.setEnabled(not use_recommended)

    def test_connection(self):
        url = self.txt_api_url.text().strip()
        key = self.txt_api_key.text().strip()
        service_name = self.txt_service_name.text().strip()

        if not url:
            QMessageBox.warning(self, "Missing URL", "Please enter a Hydrus API URL.")
            return

        if not key:
            QMessageBox.warning(self, "Missing Key", "Please enter a Hydrus API key to test.")
            return

        try:
            client = hydrus_api.Client(access_key=key, api_url=url)
            ver = client.get_api_version()
            v_num = ver.get("version", "unknown")
            msg = f"Successfully connected to Hydrus API (v{v_num})!"

            if service_name:
                services_data = client.get_services()
                target = service_name.lower()
                if len(target) == 64 and all(c in "0123456789abcdef" for c in target):
                    msg += f"\n\nUsing raw 64-character service Hex Key directly."
                else:
                    dummy_thread = TaggerThread([], url, key, service_name, 0.2, "CPU", False, False, 1, {}, [])
                    found_key = dummy_thread._find_key_in_data(services_data, target)
                    if found_key:
                        msg += f"\n\nTag Service '{service_name}' verified (Key: {found_key[:12]}...)."
                    else:
                        msg += f"\n\nWarning: Could not resolve Tag Service '{service_name}' in Hydrus."

            QMessageBox.information(self, "Connection Test", msg)
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", f"Failed to connect to Hydrus:\n{str(e)}")

    def log(self, message):
        self.log_output.append(message)

    def load_presets(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.presets = data if isinstance(data, dict) else {}
                self.preset_combo.blockSignals(True)
                self.preset_combo.clear()
                self.preset_combo.addItems(self.presets.keys())
                self.preset_combo.blockSignals(False)
                if self.presets:
                    self.on_preset_changed()
            except Exception as e:
                self.log(f"Failed to load presets: {e}")

    def save_preset(self):
        name = self.preset_combo.currentText().strip()
        if not name:
            name = "Default"
            
        self.presets[name] = {
            "api_url": self.txt_api_url.text().strip(),
            "api_key": self.txt_api_key.text().strip(),
            "service_name": self.txt_service_name.text().strip(),
            "use_namespaces": self.chk_use_namespaces.isChecked(),
            "use_fp16": self.chk_use_fp16.isChecked(),
            "batch_size": self.combo_batch_size.currentText(),
            "use_recommended": self.chk_use_recommended.isChecked(),
            "global_threshold": self.spin_threshold.value(),
            "device": self.combo_device.currentText(),
            "blacklist": self.txt_blacklist.text().strip(),
            "categories": {cat: cb.isChecked() for cat, cb in self.cat_checkboxes.items()}
        }
        
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.presets, f, indent=4)
        except IOError as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save preset to file:\n{e}")
            return
            
        self.load_presets()
        self.preset_combo.setCurrentText(name)
        QMessageBox.information(self, "Success", f"Preset '{name}' saved.")

    def delete_preset(self):
        current_text = self.preset_combo.currentText().strip()
        if not current_text or current_text not in self.presets:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete preset '{current_text}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        del self.presets[current_text]
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.presets, f, indent=4)
        except IOError as e:
            QMessageBox.critical(self, "Delete Error", f"Failed to update presets file:\n{e}")
            return

        self.load_presets()

    def on_preset_changed(self, index=None):
        preset_name = self.preset_combo.currentText()
        if preset_name in self.presets:
            p = self.presets[preset_name]
            self.txt_api_url.setText(p.get("api_url", "http://127.0.0.1:45871/"))
            self.txt_api_key.setText(p.get("api_key", ""))
            self.txt_service_name.setText(p.get("service_name", "my tags"))
            self.chk_use_namespaces.setChecked(p.get("use_namespaces", True))
            self.chk_use_fp16.setChecked(p.get("use_fp16", True))
            self.txt_blacklist.setText(p.get("blacklist", ""))
            
            batch_str = str(p.get("batch_size", "8"))
            idx_b = self.combo_batch_size.findText(batch_str)
            if idx_b >= 0:
                self.combo_batch_size.setCurrentIndex(idx_b)

            use_rec = p.get("use_recommended", True)
            self.chk_use_recommended.setChecked(use_rec)
            try:
                self.spin_threshold.setValue(float(p.get("global_threshold", 0.20)))
            except (ValueError, TypeError):
                self.spin_threshold.setValue(0.20)
            
            device = p.get("device", "Auto")
            idx = self.combo_device.findText(device)
            if idx >= 0:
                self.combo_device.setCurrentIndex(idx)

            saved_cats = p.get("categories", {})
            for cat_key, cb in self.cat_checkboxes.items():
                cb.setChecked(saved_cats.get(cat_key, True))

    def on_pipeline_loaded(self, pipeline_obj, config):
        """Cache the loaded model pipeline for subsequent batches."""
        self.cached_pipeline = pipeline_obj
        self.cached_pipeline_config = config

    def closeEvent(self, event):
        """Ensure background threads are safely interrupted when closing the window."""
        if self.thread and self.thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Tagging in Progress",
                "A tagging job is currently in progress.\n\nAre you sure you want to stop and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.thread.requestInterruption()
                self.thread.wait(2000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def process_files(self, file_paths):
        if self.thread and self.thread.isRunning():
            self.log("A tagging job is already in progress...")
            return

        api_key = self.txt_api_key.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Missing Key", "Please provide a valid Hydrus API Key.")
            return

        self.drop_area.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(file_paths))

        threshold_config = TaggerThread.RECOMMENDED_THRESHOLDS if self.chk_use_recommended.isChecked() else self.spin_threshold.value()

        try:
            batch_size = int(self.combo_batch_size.currentText())
        except ValueError:
            batch_size = 8

        enabled_categories = {cat: cb.isChecked() for cat, cb in self.cat_checkboxes.items()}
        blacklisted_tags = [t.strip() for t in self.txt_blacklist.text().split(",") if t.strip()]

        self.thread = TaggerThread(
            file_paths=file_paths,
            api_url=self.txt_api_url.text().strip(),
            api_key=api_key,
            service_name=self.txt_service_name.text().strip(),
            threshold_config=threshold_config,
            device_setting=self.combo_device.currentText(),
            use_namespaces=self.chk_use_namespaces.isChecked(),
            use_fp16=self.chk_use_fp16.isChecked(),
            batch_size=batch_size,
            enabled_categories=enabled_categories,
            blacklisted_tags=blacklisted_tags,
            cached_pipeline=self.cached_pipeline,
            cached_pipeline_config=self.cached_pipeline_config,
            parent=self
        )
        self.thread.log_signal.connect(self.log)
        self.thread.progress_signal.connect(lambda cur, total: self.progress_bar.setValue(cur))
        self.thread.finished_signal.connect(self.on_processing_finished)
        self.thread.pipeline_loaded_signal.connect(self.on_pipeline_loaded)
        self.thread.start()

    def on_processing_finished(self):
        self.drop_area.setEnabled(True)


class LoadingSplashScreen(QWidget):
    """Clean, frameless splash screen displayed while initializing heavy AI dependencies."""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.SplashScreen
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.resize(380, 150)

        # Center on primary display
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move((geo.width() - 380) // 2, (geo.height() - 150) // 2)

        self.setObjectName("SplashRoot")
        self.setStyleSheet("""
            QWidget#SplashRoot {
                background-color: #1e1e2e;
                border: 1px solid #45475a;
                border-radius: 12px;
            }
            QLabel {
                color: #cdd6f4;
                border: none;
            }
            QLabel#TitleLabel {
                font-size: 15px;
                font-weight: bold;
                color: #cdd6f4;
            }
            QLabel#StatusLabel {
                font-size: 12px;
                color: #a6adc8;
            }
            QProgressBar {
                border: 1px solid #313244;
                border-radius: 3px;
                background-color: #181825;
                height: 6px;
            }
            QProgressBar::chunk {
                background-color: #89b4fa;
                border-radius: 3px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        # App icon if present
        icon_path = os.path.join(os.path.dirname(__file__), "hydrus.ico")
        if os.path.exists(icon_path):
            icon_lbl = QLabel()
            icon_lbl.setPixmap(QIcon(icon_path).pixmap(38, 38))
            header_layout.addWidget(icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        title_lbl = QLabel("Hydrus PixAI Tagger")
        title_lbl.setObjectName("TitleLabel")
        self.status_lbl = QLabel("Loading Hydrus Tagger...")
        self.status_lbl.setObjectName("StatusLabel")
        text_layout.addWidget(title_lbl)
        text_layout.addWidget(self.status_lbl)
        header_layout.addLayout(text_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Animated pulsing mode
        layout.addWidget(self.progress_bar)

    def set_status(self, text: str):
        self.status_lbl.setText(text)
        QApplication.processEvents()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Enforce Qt's cross-platform dynamic style. 
    # This prevents native OS wrappers from overriding the text palette in Light Mode 
    # and keeps checkboxes visible and highly contrasted at all times.
    app.setStyle("Fusion") 

    splash = LoadingSplashScreen()
    splash.show()
    app.processEvents()

    splash.set_status("Loading PyTorch and AI dependencies...")
    _load_ai_dependencies()

    splash.set_status("Initializing user interface...")
    window = MainWindow()
    window.show()

    splash.close()
    sys.exit(app.exec())