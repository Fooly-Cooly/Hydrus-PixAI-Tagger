# Hydrus Network - PixAI Tagger

A standalone PyQt6 desktop application that uses local machine learning to analyze images and automatically apply tags directly to your [Hydrus Network](https://hydrusnetwork.github.io/hydrus/) client.

Powered by the `pixai-labs/pixai-tagger-v1.0` model via Hugging Face Transformers, this tool runs entirely locally on your hardware and features an instant-startup splash screen, drag-and-drop batch processing, GPU acceleration, and smart namespace routing.

---

## Features

* **100% Local Inference:** Runs locally on your machine using CPU or NVIDIA GPU (CUDA). No cloud services or third-party web APIs required after the initial model download.
* **Direct Hydrus Integration:** Communicates over your local Hydrus Client API to parse and write tags to your chosen tag services automatically.
* **Smart Namespacing:** Automatically categorizes tags into standard Hydrus namespaces (`character:`, `series:`, `creator:`, `meta:`, `style:`, `rating:`).
* **Tag Deduplication & Blacklisting:** Prevents duplicate tags and filters out unwanted tags via custom blacklists.
* **Instant Startup & UI Splash:** Zero-delay loading screen with real-time dependency status indicators (`Loading PyTorch and AI dependencies...`).
* **Windows No-Console Support:** Launch directly without keeping command prompt windows open (`hydrus_pixai_tagger.pyw` or `run.bat`).
* **Automatic Virtual Environment Detection:** The script automatically locates and invokes its project virtual environment across Windows, Linux, and macOS.
* **Interactive Batch Processing:** Drag and drop individual images or entire folder hierarchies directly into the application.
* **In-Memory Pipeline Caching:** Keeps the AI model in VRAM between drops for immediate subsequent batch evaluation.
* **Hardware & Performance Controls:** Adjust batch sizes, toggle FP16 (Half Precision) for VRAM savings, and select execution devices (Auto, CUDA, or CPU).
* **Presets System:** Save and switch between different API keys, target tag services, and threshold configurations.

---

## Prerequisites

* **Python:** 3.10 or newer (64-bit).
* **Hydrus Network:** A running instance of the Hydrus Network client with the **Client API** enabled and an API key with permission to add tags.
* **Hardware:** An NVIDIA GPU with CUDA support is recommended for fast processing, though CPU inference is fully supported.

---

## Quick Start / Installation

### 1. Clone the repository:
```bash
git clone https://github.com/Fooly-Cooly/Hydrus-PixAI-Tagger.git
cd Hydrus-PixAI-Tagger
```

### 2. Run Setup:

* **Windows:**
  Double-click `setup.bat` (or simply run `run.bat`, which will automatically offer setup on first launch). Choose your preferred PyTorch hardware engine:
  * `[1]` CUDA 12.x
  * `[2]` CUDA 13.x (Recommended for Python 3.13+ or modern RTX GPUs)
  * `[3]` CPU Only
* **Linux / macOS:**
  ```bash
  chmod +x setup.sh run.sh
  ./setup.sh
  ```

---

## Usage

### Launching the Application

* **Windows (Recommended):**
  * Double-click `run.bat` (launches and immediately closes the terminal window).
  * Or double-click `hydrus_pixai_tagger.pyw` for direct GUI execution.
* **Linux / macOS:**
  ```bash
  ./run.sh
  ```
* **Command Line:**
  ```bash
  python hydrus_pixai_tagger.py
  ```

*(Note: The first time you run an image tagging job, the application will automatically download the PixAI model from Hugging Face to a local `hf_cache` folder inside the project directory. This is a one-time download.)*

### Workflow

1. **Configure Connection:**
   * **API URL:** The address of your Hydrus client API (default: `http://127.0.0.1:45871/`).
   * **API Key:** Enter your Hydrus API access key.
   * **Tag Service:** Enter the name of the tag service in Hydrus you want to write to (e.g., `my tags`), or its raw 64-character Hex Key.
   * Click **Test Connection** to verify API connectivity and validate the target service name.
2. **Configure Tagging Rules (Optional):**
   * Keep **Use Recommended Thresholds** enabled for optimal macro-F1 confidence values per category, or uncheck it to specify a manual threshold override.
   * Toggle desired categories (General, Character, Style, Series, Artist, Meta, Rating).
   * Enter comma-separated tags in the **Tag Blacklist** to omit unwanted tags.
3. **Save Presets:**
   * Click **Save** to store your connection settings and threshold preferences under a custom preset name.
4. **Tag Images:**
   * Drag and drop image files or folders directly into the drop zone.
   * The progress bar and console log will track file hashing, inference, and Hydrus tag submissions in real time.

---

## Notes & Tips

* **First Run Model Download:** When tagging the very first batch of images, `transformers` will download and unpack the model weights into system memory/VRAM. Subsequent drops will run instantly.
* **Light/Dark Mode Theme Switching:** The application uses Qt's native "Fusion" style for cross-platform readability. If you switch your operating system theme (Light/Dark) while the app is open, restart the app to refresh the theme palette.
* **Error Reporting:** If an unhandled startup error occurs in no-console mode, a native modal error dialog will display the issue and save the complete traceback to `crash.log`.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

*Note: This tool uses the [`pixai-labs/pixai-tagger-v1.0`](https://huggingface.co/pixai-labs/pixai-tagger-v1.0) model. Please review their model license and terms on Hugging Face.*
