import json
import os
from fpdf import FPDF
import folder_paths
import datetime
import traceback
from .scanner import NodeLicenseScanner

# --- 1. Custom PDF Class for Styling ---
class PDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Register system Unicode font for full Unicode support (fixes bullet "•" error)
        self.add_font('HelveticaUnicode', '', '/System/Library/Fonts/Helvetica.ttc', uni=True)
        self.add_font('HelveticaUnicode', 'B', '/System/Library/Fonts/Helvetica.ttc', uni=True)
        self.add_font('HelveticaUnicode', 'I', '/System/Library/Fonts/Helvetica.ttc', uni=True)
        self.add_font('HelveticaUnicode', 'BI', '/System/Library/Fonts/Helvetica.ttc', uni=True)

    def header(self):
        self.set_font('HelveticaUnicode', 'B', 16)
        self.cell(0, 10, 'Workflow & Asset Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('HelveticaUnicode', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('HelveticaUnicode', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, text_lines):
        self.set_font('HelveticaUnicode', '', 10)
        for line in text_lines:
            # Use write() for more robust line breaking
            self.write(5, line + '\n')
        self.ln()

# --- 2. Main Node Class ---
class WorkflowSummary:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "output_folder": ("STRING", {"default": ""}),
                "report_type": (["Full Report (Nodes + Licenses)", "Licenses Only"], {"default": "Full Report (Nodes + Licenses)"}),
                "workflow_version": ("STRING", {"default": "1.0"}),
                "workflow_author": ("STRING", {"default": ""}),
                "include_all_installed_nodes": ("BOOLEAN", {"default": False}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "export_summary"
    CATEGORY = "utils"

    def export_summary(self, output_folder="", report_type="Full Report (Nodes + Licenses)",
                      workflow_version="1.0", workflow_author="", include_all_installed_nodes=True,
                      prompt=None, extra_pnginfo=None):
        try:
            if not prompt:
                return ("This node requires an active workflow to summarize. Please run a workflow to see the summary.",)

            # Enhanced node detection - get ALL installed nodes
            scanner = NodeLicenseScanner()

            if include_all_installed_nodes:
                all_installed_nodes = scanner.get_all_installed_nodes()
                print(f"WorkflowSummary: Found {len(all_installed_nodes)} total installed nodes")
            else:
                # Legacy mode - only custom nodes
                node_paths = scanner.get_node_paths()
                all_installed_nodes = {}

            summary = {
                "workflow_nodes": [],  # Nodes used in this workflow
                "all_installed_nodes": all_installed_nodes,  # ALL installed nodes
                "models": [],
                "metadata": {
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "version": workflow_version,
                    "author": workflow_author,
                    "report_type": report_type
                }
            }

            # Process the current workflow nodes
            for node_id, node_info in prompt.items():
                node_type = node_info['class_type']

                # Get license info from comprehensive node database or fallback
                if node_type in all_installed_nodes:
                    license_info = all_installed_nodes[node_type]['license']
                    node_category = all_installed_nodes[node_type].get('category', 'unknown')
                else:
                    # Fallback for nodes not in our database
                    license_info = self._find_node_license_legacy(node_type, scanner.get_node_paths())
                    node_category = 'unknown'

                summary["workflow_nodes"].append({
                    "id": node_id,
                    "type": node_type,
                    "license": license_info,
                    "category": node_category
                })

                # Enhanced model detection - detect ALL model types
                if "inputs" in node_info:
                    inputs = node_info["inputs"]
                    detected_models = self._detect_all_model_types(inputs, node_type)

                    for model_info in detected_models:
                        model_name = model_info['name']
                        if not any(m['name'] == model_name for m in summary['models']):
                            lic = self._load_license(model_name)
                            summary["models"].append({
                                "name": model_name,
                                "license": lic,
                                "type": model_info['type'],
                                "node_type": node_type
                            })
            
            image_data = self._get_output_image_data(prompt, extra_pnginfo)

            # --- Enhanced PDF Generation ---
            pdf = self._generate_enhanced_pdf(summary, image_data, report_type)

            # --- Save the PDF ---
            # Determine the output directory
            if output_folder and os.path.isdir(output_folder):
                output_dir = output_folder
            else:
                output_dir = folder_paths.get_output_directory()

            # Ensure the directory exists
            os.makedirs(output_dir, exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"workflow_summary_{timestamp}.pdf"
            file_path = os.path.join(output_dir, filename)
            
            pdf.output(file_path)
            return (f"Successfully exported summary to: {file_path}",)
        except Exception as e:
            error_message = f"An error occurred in WorkflowSummary: {str(e)}\n\n{traceback.format_exc()}"
            print(error_message)
            return (error_message,)

    def _detect_all_model_types(self, inputs, node_type):
        """
        Enhanced model detection - detects ALL model types, not just 3.
        Addresses maintainer requirement: "detect all types of models"
        """
        detected_models = []

        # Comprehensive model type mapping
        model_patterns = {
            # Checkpoints
            "ckpt_name": "checkpoint",
            "model_name": "checkpoint",
            "checkpoint": "checkpoint",

            # LoRA models
            "lora_name": "lora",
            "lora": "lora",
            "lycoris_name": "lycoris",

            # ControlNet models
            "control_net_name": "controlnet",
            "controlnet": "controlnet",
            "control_net": "controlnet",

            # VAE models
            "vae_name": "vae",
            "vae": "vae",

            # Upscaler models
            "upscale_model": "upscaler",
            "model": "upscaler",  # Context-dependent

            # Embedding/Textual Inversion
            "embedding": "embedding",
            "textual_inversion": "embedding",

            # Face restoration
            "face_restore_model": "face_restoration",
            "gfpgan_model": "face_restoration",

            # Other model types
            "clip_name": "clip",
            "unet_name": "unet",
            "sampler_name": "sampler",
        }

        for input_key, input_value in inputs.items():
            if isinstance(input_value, str) and input_value.strip():
                # Check if this input matches any model pattern
                for pattern, model_type in model_patterns.items():
                    if pattern in input_key.lower():
                        # Special handling for context-dependent types
                        if pattern == "model" and node_type:
                            if "upscale" in node_type.lower():
                                model_type = "upscaler"
                            elif "controlnet" in node_type.lower():
                                model_type = "controlnet"
                            elif "face" in node_type.lower():
                                model_type = "face_restoration"

                        detected_models.append({
                            "name": input_value,
                            "type": model_type,
                            "input_key": input_key
                        })
                        break

        return detected_models

    def _generate_enhanced_pdf(self, summary, image_data, report_type):
        """
        Enhanced PDF generation with metadata, license legend, and report type options.
        Addresses maintainer requirements for metadata and license legend.
        """
        pdf = PDF()
        pdf.add_page()
        pdf.set_title('Enhanced Workflow & Asset Report')

        # --- Header with Metadata ---
        pdf.chapter_title('Report Information')
        metadata_lines = [
            f"Generated: {summary['metadata']['date']}",
            f"Workflow Version: {summary['metadata']['version']}",
            f"Author: {summary['metadata']['author'] or 'Not specified'}",
            f"Report Type: {summary['metadata']['report_type']}"
        ]
        pdf.chapter_body(metadata_lines)

        # --- License Legend ---
        pdf.chapter_title('License Legend')
        legend_lines = self._get_license_legend()
        pdf.chapter_body(legend_lines)

        if report_type == "Full Report (Nodes + Licenses)":
            # --- All Installed Nodes Section ---
            if summary.get('all_installed_nodes'):
                pdf.chapter_title(f'All Installed Nodes ({len(summary["all_installed_nodes"])} total)')

                # Group by type
                core_nodes = [n for n in summary['all_installed_nodes'].values() if n['type'] == 'core']
                custom_nodes = [n for n in summary['all_installed_nodes'].values() if n['type'] == 'custom']

                if core_nodes:
                    pdf.set_font('HelveticaUnicode', 'B', 11)
                    pdf.cell(0, 8, f'ComfyUI Core Nodes ({len(core_nodes)})', 0, 1)
                    pdf.set_font('HelveticaUnicode', '', 9)

                    core_lines = []
                    for node in sorted(core_nodes, key=lambda x: x['name']):
                        core_lines.append(f"• {node['name']} ({node.get('category', 'unknown')}) - {node['license']}")
                    pdf.chapter_body(core_lines)

                if custom_nodes:
                    pdf.set_font('HelveticaUnicode', 'B', 11)
                    pdf.cell(0, 8, f'Custom Nodes ({len(custom_nodes)})', 0, 1)
                    pdf.set_font('HelveticaUnicode', '', 9)

                    custom_lines = []
                    for node in sorted(custom_nodes, key=lambda x: x['name']):
                        package = node.get('package', 'unknown')
                        custom_lines.append(f"• {node['name']} ({node.get('category', 'unknown')}) - Package: {package}")
                    pdf.chapter_body(custom_lines)

            # --- Workflow Nodes Section ---
            pdf.chapter_title(f'Nodes Used in This Workflow ({len(summary["workflow_nodes"])})')
            workflow_lines = []
            for node in summary["workflow_nodes"]:
                workflow_lines.append(f"ID: {node['id']}, Type: {node['type']} ({node.get('category', 'unknown')})")
                workflow_lines.append(f"License: {node['license']}")
                workflow_lines.append("")  # Empty line for spacing
            pdf.chapter_body(workflow_lines)

        # --- Models & Licenses Section (always included) ---
        if summary["models"]:
            pdf.chapter_title(f'Models & Licenses ({len(summary["models"])} total)')

            # Group models by type
            models_by_type = {}
            for model in summary["models"]:
                model_type = model.get('type', 'unknown')
                if model_type not in models_by_type:
                    models_by_type[model_type] = []
                models_by_type[model_type].append(model)

            for model_type, models in sorted(models_by_type.items()):
                pdf.set_font('HelveticaUnicode', 'B', 10)
                pdf.cell(0, 6, f'{model_type.title()} Models ({len(models)})', 0, 1)
                pdf.set_font('HelveticaUnicode', '', 9)

                model_lines = []
                for model in sorted(models, key=lambda x: x['name']):
                    model_lines.append(f"• {model['name']}")
                    model_lines.append(f"  License: {model['license']}")
                    model_lines.append(f"  Used in: {model.get('node_type', 'unknown')} node")
                    model_lines.append("")  # Spacing
                pdf.chapter_body(model_lines)

        # --- Generated Images & Prompts (only in full report) ---
        if report_type == "Full Report (Nodes + Licenses)" and image_data:
            pdf.chapter_title('Generated Images & Prompts')
            for img_info in image_data:
                img_path = img_info['path']
                prompt_text = img_info.get('prompt', 'N/A')
                negative_prompt_text = img_info.get('negative_prompt', 'N/A')

                pdf.set_font('HelveticaUnicode', 'B', 10)
                pdf.cell(0, 5, f"Image: {os.path.basename(img_path)}", 0, 1)
                pdf.set_font('HelveticaUnicode', '', 9)

                # Calculate available width for multi_cell
                available_width = pdf.w - pdf.l_margin - pdf.r_margin

                pdf.multi_cell(available_width, 4, f"Prompt: {prompt_text}")
                pdf.multi_cell(available_width, 4, f"Negative Prompt: {negative_prompt_text}")
                pdf.ln(2)

                try:
                    # Ensure image width also respects margins
                    image_width = pdf.w - 2 * pdf.l_margin
                    pdf.image(img_path, w=image_width)
                    pdf.ln(5)
                except Exception as e:
                    pdf.chapter_body([f"Could not embed image {os.path.basename(img_path)}: {e}"])

        return pdf

    def _get_license_legend(self):
        """Generate license legend explaining common licenses"""
        return [
            "MIT License: Permissive license allowing commercial use with attribution",
            "Apache-2.0: Permissive license with patent protection",
            "CreativeML Open RAIL-M: Responsible AI license with usage restrictions",
            "CreativeML Open RAIL++-M: Enhanced responsible AI license",
            "BSD-3-Clause: Permissive license similar to MIT",
            "GPL-3.0: Copyleft license requiring derivative works to be open source",
            "Unknown: License information not available or could not be determined",
            "",
            "Note: Always verify license terms before commercial use."
        ]

    def _find_node_license_legacy(self, node_type, node_paths):
        """Legacy method for finding node licenses when not in comprehensive database"""
        return self._find_node_license(node_type, node_paths)

    def _find_node_license(self, node_type, node_paths):
        # Dynamically extract native ComfyUI node class names from nodes.py
        native_nodes_path = os.path.expanduser("~/ComfyUI/nodes.py")
        native_node_types = set()
        try:
            with open(native_nodes_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            in_dict = False
            for line in lines:
                if "NODE_CLASS_MAPPINGS" in line and "=" in line and "{" in line:
                    in_dict = True
                    continue
                if in_dict:
                    if "}" in line:
                        break
                    # Extract key before colon, strip quotes and whitespace
                    if ":" in line:
                        key = line.split(":")[0].strip().strip('"').strip("'")
                        if key:
                            native_node_types.add(key)
        except Exception as e:
            # Fallback: treat as no native nodes found
            native_node_types = set()

        if node_type in native_node_types:
            return "ComfyUI Native (MIT License)"

        node_path = node_paths.get(node_type)
        if not node_path:
            return "Unknown"

        try:
            search_dir = os.path.dirname(node_path)
            # Limit search to the custom_nodes directory
            custom_nodes_root = folder_paths.get_folder_paths("custom_nodes")[0]
    
            for i in range(5): # Search up to 5 parent directories
                print(f"[LicenseTraversal] Checking directory: {search_dir} (level {i+1})")
                try:
                    files_in_dir = os.listdir(search_dir)
                    print(f"[LicenseTraversal] Files in {search_dir}: {files_in_dir}")
                except Exception as e:
                    print(f"[LicenseTraversal] Could not list files in {search_dir}: {e}")
                    break
    
                for filename in files_in_dir:
                    if filename.lower() in ('license', 'license.md', 'license.txt'):
                        print(f"[LicenseTraversal] Found license file: {filename} in {search_dir}")
                        with open(os.path.join(search_dir, filename), 'r', encoding='utf-8') as f:
                            # Return the first line of the license
                            return f.readline().strip()
                
                if search_dir == custom_nodes_root:
                    print(f"[LicenseTraversal] Reached custom_nodes_root: {custom_nodes_root}, stopping traversal.")
                    break
                parent_dir = os.path.dirname(search_dir)
                if parent_dir == search_dir:
                    print(f"[LicenseTraversal] Reached filesystem root at {search_dir}, stopping traversal.")
                    break
                search_dir = parent_dir
    
        except Exception as e:
            print(f"[LicenseTraversal] Exception during traversal: {e}")
            return f"Error finding license: {e}"
                
        print(f"[LicenseTraversal] License not found for node_type: {node_type}")
        return "Not Found"

    def _get_output_image_data(self, prompt, extra_pnginfo):
        image_data = []
        output_dir = folder_paths.get_output_directory()
        
        nodes_by_id = {node_id: info for node_id, info in prompt.items()}
        
        save_image_nodes = {node_id: info for node_id, info in prompt.items() if info['class_type'] == 'SaveImage'}
        if not save_image_nodes:
            return []

        try:
            all_files = sorted([os.path.join(output_dir, f) for f in os.listdir(output_dir)], key=os.path.getctime, reverse=True)
        except FileNotFoundError:
            return []

        # Extract links from extra_pnginfo if available, as it contains the full workflow
        links = []
        if extra_pnginfo and 'workflow' in extra_pnginfo and 'links' in extra_pnginfo['workflow']:
            links = extra_pnginfo['workflow']['links']
        elif 'links' in prompt: # Fallback if links are directly in prompt (less common for full workflow)
            links = prompt['links']

        for save_node_id, save_node_info in save_image_nodes.items():
            prefix = save_node_info['inputs']['filename_prefix']
            
            found_image_path = None
            for f_path in all_files:
                filename = os.path.basename(f_path)
                if filename.startswith(prefix) and filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    found_image_path = f_path
                    break
            
            if found_image_path:
                prompts = self._trace_prompts_for_node(save_node_id, nodes_by_id, links)
                image_data.append({
                    'path': found_image_path,
                    'prompt': prompts.get('positive', 'Prompt Not Found'),
                    'negative_prompt': prompts.get('negative', 'Negative Prompt Not Found')
                })
        return image_data

    def _trace_prompts_for_node(self, start_node_id, nodes, links):
        """Traces back from a starting node to find positive and negative prompts."""
        prompts = {}
        
        # Create a reverse mapping of links for easier traversal
        reverse_links = {}
        for link_info in links: # links is a list of lists, not a dict
            link_id, source_node_id, source_output_idx, dest_node_id, dest_input_idx, link_type = link_info
            
            dest_node_id_str = str(dest_node_id)
            source_node_id_str = str(source_node_id)

            dest_node_info = nodes.get(dest_node_id_str)
            if dest_node_info and 'inputs' in dest_node_info:
                # Find the input name corresponding to the index
                input_name = None
                # ComfyUI inputs can be a list of dicts or a dict of dicts
                if isinstance(dest_node_info['inputs'], list):
                    for input_def in dest_node_info['inputs']:
                        if input_def.get('link') == link_id:
                            input_name = input_def.get('name')
                            break
                elif isinstance(dest_node_info['inputs'], dict):
                    # This is a more complex case, often inputs are by index in links
                    # We need to map dest_input_idx to input name
                    # This is a heuristic, as ComfyUI's internal structure can vary
                    # For now, we'll rely on the link_info[4] (dest_input_idx)
                    pass # We'll try to infer input name later if needed

                if input_name is None: # Fallback for cases where input name isn't directly found
                    # Try to infer input name from common patterns or link type
                    if dest_node_info['class_type'] == 'KSampler':
                        if dest_input_idx == 1: input_name = 'positive' # Heuristic for KSampler
                        elif dest_input_idx == 2: input_name = 'negative' # Heuristic for KSampler
                    elif link_type == 'CONDITIONING':
                        # This is a very loose heuristic
                        input_name = 'conditioning'
                    elif link_type == 'STRING':
                        input_name = 'text' # Common for text inputs

                if input_name:
                    if dest_node_id_str not in reverse_links:
                        reverse_links[dest_node_id_str] = []
                    
                    reverse_links[dest_node_id_str].append({
                        "source_node_id": source_node_id_str,
                        "source_output_idx": source_output_idx,
                        "dest_input_name": input_name
                    })

        # Recursive function to trace back
        def find_text_in_ancestors(node_id, visited):
            if node_id in visited:
                return None
            visited.add(node_id)

            node_info = nodes.get(node_id)
            if not node_info:
                return None

            # Base case: Found a node that contains a text widget or input
            if node_info['class_type'] == 'CLIPTextEncode' and 'inputs' in node_info and 'text' in node_info['inputs']:
                return node_info['inputs']['text']
            
            # Check for text in widgets_values (for simple text input nodes)
            if 'widgets_values' in node_info and node_info['widgets_values']:
                # Heuristic: assume the first widget value is the text
                return str(node_info['widgets_values'][0])

            # Recursive step: traverse to parent nodes
            if node_id in reverse_links:
                for link in reverse_links[node_id]:
                    found_text = find_text_in_ancestors(link['source_node_id'], visited)
                    if found_text:
                        return found_text
            return None

        # Start tracing from the KSampler or equivalent node that feeds into SaveImage
        image_source_node_id = None
        if str(start_node_id) in reverse_links:
            for link in reverse_links[str(start_node_id)]:
                # Assuming the image is the first input or named 'images'
                if link['dest_input_name'] == 'images' or link['dest_input_name'] == 'pixels': # Common image input names
                    image_source_node_id = link['source_node_id']
                    break
        
        if image_source_node_id:
            # Now, from the image source node, find its positive and negative inputs
            if image_source_node_id in reverse_links:
                for link in reverse_links[image_source_node_id]:
                    if link['dest_input_name'] == 'positive':
                        prompts['positive'] = find_text_in_ancestors(link['source_node_id'], set())
                    elif link['dest_input_name'] == 'negative':
                        prompts['negative'] = find_text_in_ancestors(link['source_node_id'], set())

        return prompts

    def _load_license(self, model_name):
        import requests

        def debug(msg):
            print(f"[WorkflowSummary][LicenseLookup] {msg}")

        # 1. Try local mapping
        path = os.path.join(os.path.dirname(__file__), "model_licenses.json")
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            base_model_name = os.path.basename(model_name)
            license_val = data.get(base_model_name, data.get(model_name))
            debug(f"Local mapping: {base_model_name} -> {license_val}")
            if license_val:
                return license_val
        except Exception as e:
            debug(f"Local mapping exception: {e}")

        # 2. Try HuggingFace direct repo_id lookup
        def try_hf_lookup(repo_id):
            url = f"https://huggingface.co/api/models/{repo_id}"
            debug(f"Trying HuggingFace direct lookup: {url}")
            try:
                resp = requests.get(url, timeout=5)
                debug(f"Direct lookup status: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    debug(f"Direct lookup result: {data.get('license', None)}")
                    return data.get("license", None)
            except Exception as e:
                debug(f"Direct lookup exception: {e}")
            return None

        # 2a. Try direct lookup by filename (legacy, may fail)
        repo_id = os.path.splitext(os.path.basename(model_name))[0]
        license_val = try_hf_lookup(repo_id)
        if license_val:
            debug(f"Direct HuggingFace license found: {license_val}")
            return f"HuggingFace: {license_val}"

        # 2b. Try HuggingFace search API if direct lookup fails
        def try_hf_search(model_name):
            import re
            base_name = os.path.splitext(os.path.basename(model_name))[0]
            alphanum = re.sub(r'[^a-zA-Z0-9]', '', base_name)
            search_key = alphanum[:6] if len(alphanum) >= 6 else alphanum
            url = f"https://huggingface.co/api/models?search={search_key}"
            debug(f"Trying HuggingFace search: {url}")
            try:
                resp = requests.get(url, timeout=5)
                debug(f"Search status: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    debug(f"Search results: {[repo.get('modelId') for repo in data]}")
                    if isinstance(data, list) and data:
                        def score(repo):
                            rid = repo.get("modelId", "").lower()
                            if base_name.lower() in rid:
                                return 2
                            if rid.startswith(search_key.lower()):
                                return 1
                            return 0
                        best = max(data, key=score)
                        repo_id = best.get("modelId")
                        debug(f"Best match repo_id: {repo_id}")
                        if repo_id:
                            license_val = try_hf_lookup(repo_id)
                            if license_val:
                                debug(f"Search HuggingFace license found: {license_val}")
                                return f"HuggingFace: {license_val} (from search: {repo_id})"
                            # If not found, try to get license from model card metadata (more robust)
                            url_meta = f"https://huggingface.co/api/models/{repo_id}"
                            try:
                                resp_meta = requests.get(url_meta, timeout=5)
                                debug(f"Meta lookup status: {resp_meta.status_code}")
                                if resp_meta.status_code == 200:
                                    meta = resp_meta.json()
                                    # Try to find license in meta fields
                                    for k in ["license", "cardData", "modelCardData"]:
                                        if k in meta and meta[k]:
                                            if isinstance(meta[k], dict):
                                                # Look for license in nested dict
                                                for subk in ["license", "license_name"]:
                                                    if subk in meta[k] and meta[k][subk]:
                                                        debug(f"Meta nested license found: {meta[k][subk]}")
                                                        return f"HuggingFace: {meta[k][subk]} (from meta: {repo_id})"
                                            elif isinstance(meta[k], str):
                                                debug(f"Meta license found: {meta[k]}")
                                                return f"HuggingFace: {meta[k]} (from meta: {repo_id})"
                            except Exception as e:
                                debug(f"Meta lookup exception: {e}")
            except Exception as e:
                debug(f"Search exception: {e}")
            return None

        license_val = try_hf_search(model_name)
        if license_val:
            return license_val

        # 3. Try CivitAI API
        def try_civitai_lookup(model_name):
            civitai_name = os.path.splitext(os.path.basename(model_name))[0]
            url = f"https://civitai.com/api/v1/models?query={civitai_name}"
            debug(f"Trying CivitAI lookup: {url}")
            try:
                resp = requests.get(url, timeout=5)
                debug(f"CivitAI status: {resp.status_code}")
                if resp.status_code == 200:
                    data = resp.json()
                    debug(f"CivitAI results: {data.get('items', [])}")
                    if "items" in data and data["items"]:
                        item = data["items"][0]
                        if "modelVersions" in item and item["modelVersions"]:
                            mv = item["modelVersions"][0]
                            if "license" in mv and mv["license"]:
                                debug(f"CivitAI license found: {mv['license']}")
                                return f"CivitAI: {mv['license']}"
                        if "license" in item and item["license"]:
                            debug(f"CivitAI license found: {item['license']}")
                            return f"CivitAI: {item['license']}"
            except Exception as e:
                debug(f"CivitAI exception: {e}")
            return None

        license_val = try_civitai_lookup(model_name)
        if license_val:
            return license_val

        debug("No license found, returning 'unknown'")
        return "unknown"
