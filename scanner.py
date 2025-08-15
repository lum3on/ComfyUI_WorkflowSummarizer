import os
import json
import re
import folder_paths

class NodeLicenseScanner:
    def __init__(self):
        self.custom_nodes_path = folder_paths.get_folder_paths("custom_nodes")[0]
        self.cache_file = os.path.join(os.path.dirname(__file__), 'node_paths.json')
        self.all_nodes_cache = os.path.join(os.path.dirname(__file__), 'all_nodes.json')

    def get_comfyui_core_nodes(self):
        """
        Detects ComfyUI core nodes from the main ComfyUI installation.
        Tries multiple common ComfyUI installation paths.
        """
        print("NodeLicenseScanner: Scanning ComfyUI core nodes...")
        core_nodes = {}

        # Try multiple possible ComfyUI installation paths
        possible_paths = [
            os.path.expanduser("~/ComfyUI/nodes.py"),
            os.path.join(os.path.dirname(self.custom_nodes_path), "nodes.py"),
            os.path.join(os.path.dirname(os.path.dirname(self.custom_nodes_path)), "nodes.py"),
            "/ComfyUI/nodes.py",
            "./ComfyUI/nodes.py",
            "../ComfyUI/nodes.py",
            "../../ComfyUI/nodes.py"
        ]

        for nodes_path in possible_paths:
            if os.path.exists(nodes_path):
                print(f"NodeLicenseScanner: Found ComfyUI nodes.py at: {nodes_path}")
                try:
                    with open(nodes_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Extract NODE_CLASS_MAPPINGS
                    mapping_match = re.search(r"NODE_CLASS_MAPPINGS\s*=\s*\{([^}]+)\}", content, re.DOTALL)
                    if mapping_match:
                        dict_content = mapping_match.group(1)
                        class_names = re.findall(r"['\"]([^'\"]+)['\"]\s*:", dict_content)

                        for name in class_names:
                            core_nodes[name] = {
                                "name": name,
                                "file_path": nodes_path,
                                "type": "core",
                                "license": "ComfyUI Native (MIT License)",
                                "category": self._categorize_core_node(name)
                            }

                        print(f"NodeLicenseScanner: Found {len(core_nodes)} core nodes")
                        break

                except Exception as e:
                    print(f"NodeLicenseScanner: Error reading {nodes_path}: {e}")
                    continue

        # Fallback: Add essential core nodes if none found
        if not core_nodes:
            print("NodeLicenseScanner: No core nodes found, using fallback list")
            fallback_nodes = [
                "KSampler", "CLIPTextEncode", "CheckpointLoaderSimple", "SaveImage",
                "VAEDecode", "VAEEncode", "LoraLoader", "ControlNetLoader",
                "EmptyLatentImage", "LoadImage", "PreviewImage"
            ]
            for name in fallback_nodes:
                core_nodes[name] = {
                    "name": name,
                    "file_path": "ComfyUI/nodes.py",
                    "type": "core",
                    "license": "ComfyUI Native (MIT License)",
                    "category": self._categorize_core_node(name)
                }

        return core_nodes

    def _categorize_core_node(self, node_name):
        """Categorize core nodes by their function"""
        if any(x in node_name.lower() for x in ['sampler', 'sample']):
            return "sampling"
        elif any(x in node_name.lower() for x in ['clip', 'text', 'encode']):
            return "conditioning"
        elif any(x in node_name.lower() for x in ['checkpoint', 'loader', 'load']):
            return "loaders"
        elif any(x in node_name.lower() for x in ['save', 'preview', 'image']):
            return "output"
        elif any(x in node_name.lower() for x in ['vae', 'decode', 'encode']):
            return "vae"
        elif any(x in node_name.lower() for x in ['control', 'lora']):
            return "conditioning"
        else:
            return "utility"

    def scan_all_installed_nodes(self):
        """
        Comprehensive scan of ALL installed nodes (core + custom).
        This addresses the maintainer's requirement to detect ALL installed nodes.
        """
        print("NodeLicenseScanner: Starting comprehensive scan of ALL installed nodes...")

        # Get core nodes
        all_nodes = self.get_comfyui_core_nodes()

        # Get custom nodes
        custom_nodes = self.scan_custom_nodes_enhanced()

        # Merge them
        all_nodes.update(custom_nodes)

        print(f"NodeLicenseScanner: Total nodes found: {len(all_nodes)} (Core: {len([n for n in all_nodes.values() if n['type'] == 'core'])}, Custom: {len([n for n in all_nodes.values() if n['type'] == 'custom'])})")

        # Cache the results
        self._write_all_nodes_cache(all_nodes)

        return all_nodes

    def scan_custom_nodes_enhanced(self):
        """
        Enhanced custom node scanning with better categorization.
        """
        print("NodeLicenseScanner: Scanning custom nodes...")
        custom_nodes = {}

        # Regex patterns for finding node mappings
        mapping_regex = re.compile(r"NODE_CLASS_MAPPINGS\s*=\s*\{([^}]+)\}", re.DOTALL)
        class_name_regex = re.compile(r"['\"]([^'\"]+)['\"]\s*:")

        for root, _, files in os.walk(self.custom_nodes_path):
            # Skip our own directory
            if os.path.abspath(root) == os.path.dirname(os.path.abspath(__file__)):
                continue

            for file in files:
                if file.endswith('.py'):
                    module_path = os.path.join(root, file)
                    try:
                        with open(module_path, 'r', encoding='utf-8') as f:
                            content = f.read()

                        match = mapping_regex.search(content)
                        if match:
                            dict_content = match.group(1)
                            class_names = class_name_regex.findall(dict_content)

                            # Get the custom node package name
                            package_name = os.path.basename(os.path.dirname(module_path))
                            if package_name == os.path.basename(self.custom_nodes_path):
                                package_name = os.path.basename(module_path).replace('.py', '')

                            for name in class_names:
                                custom_nodes[name] = {
                                    "name": name,
                                    "file_path": module_path,
                                    "type": "custom",
                                    "package": package_name,
                                    "category": self._categorize_custom_node(name, content),
                                    "license": "Unknown (Custom Node)"
                                }

                    except Exception as e:
                        # Silently continue on parse errors
                        pass

        print(f"NodeLicenseScanner: Found {len(custom_nodes)} custom nodes")
        return custom_nodes

    def _categorize_custom_node(self, node_name, content):
        """Categorize custom nodes based on name and content analysis"""
        name_lower = node_name.lower()
        content_lower = content.lower()

        # Check for specific patterns
        if any(x in name_lower for x in ['controlnet', 'control']):
            return "controlnet"
        elif any(x in name_lower for x in ['lora', 'lycoris']):
            return "lora"
        elif any(x in name_lower for x in ['upscale', 'esrgan', 'realesrgan']):
            return "upscaling"
        elif any(x in name_lower for x in ['face', 'restore', 'gfpgan']):
            return "face_restoration"
        elif any(x in name_lower for x in ['inpaint', 'outpaint']):
            return "inpainting"
        elif any(x in name_lower for x in ['animate', 'video']):
            return "animation"
        elif any(x in name_lower for x in ['text', 'prompt']):
            return "text_processing"
        elif any(x in name_lower for x in ['save', 'load', 'export']):
            return "io"
        else:
            return "utility"

    def scan_nodes_safely(self):
        """
        Scans all custom nodes using safe text parsing and maps them to their file paths.
        This method does NOT execute any node code.
        """
        print("NodeLicenseScanner: Starting safe, text-based scan of custom nodes...")
        node_paths = {}
        
        # Regex to find assignments to NODE_CLASS_MAPPINGS
        # This looks for "NODE_CLASS_MAPPINGS = {" and captures the dictionary content
        mapping_regex = re.compile(r"NODE_CLASS_MAPPINGS\s*=\s*\{([^}]+)\}", re.DOTALL)
        # Regex to find the class names (keys) in the mapping
        class_name_regex = re.compile(r"['\"]([^'\"]+)['\"]\s*:")

        for root, _, files in os.walk(self.custom_nodes_path):
            # Exclude our own directory from the scan to prevent loops
            if os.path.abspath(root) == os.path.dirname(os.path.abspath(__file__)):
                continue

            for file in files:
                if file.endswith('.py'):
                    module_path = os.path.join(root, file)
                    try:
                        with open(module_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        match = mapping_regex.search(content)
                        if match:
                            # Extract the content of the dictionary
                            dict_content = match.group(1)
                            # Find all class names (keys) within the dictionary
                            class_names = class_name_regex.findall(dict_content)
                            for name in class_names:
                                node_paths[name] = module_path

                    except Exception as e:
                        # print(f"Could not parse {module_path}: {e}")
                        pass
        
        self._write_cache(node_paths)
        print(f"NodeLicenseScanner: Safe scan complete. Found {len(node_paths)} nodes.")
        return node_paths

    def get_all_installed_nodes(self):
        """
        Gets ALL installed nodes (core + custom) with caching.
        This is the main method to use for comprehensive node detection.
        """
        if os.path.exists(self.all_nodes_cache):
            print("NodeLicenseScanner: Loading all nodes from cache.")
            with open(self.all_nodes_cache, 'r') as f:
                return json.load(f)
        else:
            return self.scan_all_installed_nodes()

    def get_node_paths(self):
        """
        Legacy method - loads node paths from cache if it exists, otherwise performs a full, safe scan.
        """
        if os.path.exists(self.cache_file):
            print("NodeLicenseScanner: Loading node paths from cache.")
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        else:
            return self.scan_nodes_safely()

    def _write_cache(self, data):
        with open(self.cache_file, 'w') as f:
            json.dump(data, f, indent=4)

    def _write_all_nodes_cache(self, data):
        with open(self.all_nodes_cache, 'w') as f:
            json.dump(data, f, indent=4)
