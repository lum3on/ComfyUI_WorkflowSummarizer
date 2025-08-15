import json
import os
from fpdf import FPDF
import folder_paths
import datetime
import traceback
from .scanner import NodeLicenseScanner

# --- 1. Custom PDF Class for Styling ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Workflow & Asset Report', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, text_lines):
        self.set_font('Arial', '', 10)
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
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ("STRING",)
    FUNCTION = "export_summary"
    CATEGORY = "utils"

    def export_summary(self, output_folder="", prompt=None, extra_pnginfo=None):
        try:
            if not prompt:
                return ("This node requires an active workflow to summarize. Please run a workflow to see the summary.",)

            # Load node paths on demand for a stateless execution
            scanner = NodeLicenseScanner()
            node_paths = scanner.get_node_paths()

            summary = {"nodes": [], "models": []}
            
            # Process the current workflow directly from the prompt
            for node_id, node_info in prompt.items():
                node_type = node_info['class_type']
                license_info = self._find_node_license(node_type, node_paths)
                
                summary["nodes"].append({
                    "id": node_id,
                    "type": node_type,
                    "license": license_info
                })

                if "inputs" in node_info:
                    inputs = node_info["inputs"]
                    model_name = next((inputs[key] for key in ["ckpt_name", "model_name", "lora_name"] if key in inputs), None)
                    if model_name and not any(m['name'] == model_name for m in summary['models']):
                        lic = self._load_license(model_name)
                        summary["models"].append({"name": model_name, "license": lic})
            
            image_data = self._get_output_image_data(prompt, extra_pnginfo)

            # --- PDF Generation ---
            pdf = PDF()
            pdf.add_page()
            pdf.set_title('Workflow & Asset Report')

            pdf.chapter_title('Nodes & Licenses')
            node_lines = [f"ID: {node['id']}, Type: {node['type']}\nLicense: {node['license']}" for node in summary["nodes"]]
            pdf.chapter_body(node_lines)

            if summary["models"]:
                pdf.chapter_title('Models & Licenses')
                model_lines = [f"Name: {m['name']}, License: {m['license']}" for m in summary["models"]]
                pdf.chapter_body(model_lines)
    
            if image_data:
                pdf.chapter_title('Generated Images & Prompts')
                for img_info in image_data:
                    img_path = img_info['path']
                    prompt_text = img_info.get('prompt', 'N/A')
                    negative_prompt_text = img_info.get('negative_prompt', 'N/A')

                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(0, 5, f"Image: {os.path.basename(img_path)}", 0, 1)
                    pdf.set_font('Arial', '', 9)
                    
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

    def _find_node_license(self, node_type, node_paths):
        node_path = node_paths.get(node_type)
        if not node_path:
            return "Unknown"

        try:
            search_dir = os.path.dirname(node_path)
            # Limit search to the custom_nodes directory
            custom_nodes_root = folder_paths.get_folder_paths("custom_nodes")[0]

            for _ in range(5): # Search up to 5 parent directories
                for filename in os.listdir(search_dir):
                    if filename.lower() in ('license', 'license.md', 'license.txt'):
                        with open(os.path.join(search_dir, filename), 'r', encoding='utf-8') as f:
                            # Return the first line of the license
                            return f.readline().strip()
                
                if search_dir == custom_nodes_root:
                    break
                search_dir = os.path.dirname(search_dir)

        except Exception as e:
            return f"Error finding license: {e}"
            
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
        path = os.path.join(os.path.dirname(__file__), "model_licenses.json")
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            base_model_name = os.path.basename(model_name)
            return data.get(base_model_name, data.get(model_name, "unknown"))
        except FileNotFoundError:
            return "model_licenses.json not found"