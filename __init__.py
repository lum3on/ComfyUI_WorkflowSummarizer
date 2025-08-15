from .workflow_summary import WorkflowSummary

NODE_CLASS_MAPPINGS = {
    "WorkflowSummary": WorkflowSummary
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WorkflowSummary": "Workflow Summary"
}

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']