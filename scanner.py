import os
import json
import re
import folder_paths

class NodeLicenseScanner:
    def __init__(self):
        self.custom_nodes_path = folder_paths.get_folder_paths("custom_nodes")[0]
        self.cache_file = os.path.join(os.path.dirname(__file__), 'node_paths.json')

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

    def get_node_paths(self):
        """
        Loads node paths from cache if it exists, otherwise performs a full, safe scan.
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
