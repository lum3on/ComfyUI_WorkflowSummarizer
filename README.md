# ComfyUI Workflow Summary Node

This custom node for [ComfyUI](https://github.com/comfyanonymous/ComfyUI) generates a PDF report summarizing the nodes, models, licenses, and output images in the currently-executed workflow.

## Features

- **Node & Model Listing:** Lists all nodes and models used in the workflow, including their license information.
- **License Detection:** 
  - Checks a local mapping file (`model_licenses.json`).
  - Falls back to HuggingFace API for public models.
  - Falls back to CivitAI API for CivitAI models.
- **Native Node Detection:** Dynamically parses ComfyUI's `nodes.py` to identify and label native nodes as "ComfyUI Native (MIT License)".
- **Image & Prompt Tracing:** Embeds output images and traces back to show the positive/negative prompts used to generate them.
- **Custom Output Folder:** Lets you specify the output folder for the generated PDF.
- **Stateless:** No caching; always reflects the current workflow.

## Installation

1. Place this folder in your `ComfyUI/custom_nodes/` directory.
2. Install dependencies:
   ```
   pip install fpdf2 requests
   ```
3. (Optional) Edit `model_licenses.json` to add/override model license mappings.

## Usage

- Add the **Workflow Summary** node to your ComfyUI workflow.
- Optionally set the `output_folder` input to control where the PDF is saved.
- Run your workflow. The node will generate a PDF report in the specified folder (or the default output folder).

## How License Lookup Works

1. **Local Mapping:** Checks `model_licenses.json` for a license entry.
2. **HuggingFace API:** If not found, queries HuggingFace for the model's license.
3. **CivitAI API:** If still not found, queries CivitAI for the model's license.
4. **Unknown:** If all else fails, reports "unknown".

## Limitations

- HuggingFace and CivitAI lookups require internet access.
- Model filename must match the repo or civitai model name for automatic lookup.
- Not all models provide license info in their metadata.

## Contributing

- PRs to improve prompt tracing, model detection, or license mapping are welcome!
- If you have a large mapping file for models/licenses, consider sharing it.

## License

MIT (for this node). See ComfyUI and model licenses for their respective terms.
