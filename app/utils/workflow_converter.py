"""
Universal Workflow Converter
Supports importing workflows from multiple automation platforms:
- ComfyUI (AI image generation workflows)
- n8n (General automation)
- Node-RED (IoT/event-driven automation)
- Home Assistant (Smart home automation)
- Make.com/Integromat (Business automation)
- Zapier (No direct JSON, but we parse webhook configs)
- Apache Airflow (Data pipeline DAGs - limited)
- Activepieces (Open-source automation)
- Windmill (Developer-focused automation)

Each platform has its own JSON structure, and this module converts them
to our unified workflow format.
"""

import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class WorkflowPlatform(Enum):
    """Supported workflow platforms"""
    COMFYUI = "comfyui"
    N8N = "n8n"
    NODE_RED = "node-red"
    HOME_ASSISTANT = "home-assistant"
    MAKE = "make"
    ACTIVEPIECES = "activepieces"
    WINDMILL = "windmill"
    PIPEDREAM = "pipedream"
    UNKNOWN = "unknown"


@dataclass
class WorkflowNode:
    """Universal node representation"""
    id: str
    type: str
    name: str
    platform_type: str  # Original type from the platform
    inputs: Dict = field(default_factory=dict)
    outputs: Dict = field(default_factory=dict)
    config: Dict = field(default_factory=dict)
    position: Tuple[int, int] = (0, 0)
    connections: List[str] = field(default_factory=list)  # Connected node IDs


class UniversalWorkflowConverter:
    """
    Converts workflows from various platforms to our unified format.
    """
    
    def __init__(self):
        self.nodes: Dict[str, WorkflowNode] = {}
        self.platform: WorkflowPlatform = WorkflowPlatform.UNKNOWN
        self.metadata: Dict = {}
    
    def detect_platform(self, workflow_json: Dict) -> WorkflowPlatform:
        """Auto-detect which platform the workflow is from"""
        
        # n8n detection
        if "nodes" in workflow_json and any(
            n.get("type", "").startswith("n8n-nodes") 
            for n in workflow_json.get("nodes", [])
        ):
            return WorkflowPlatform.N8N
        
        # Node-RED detection
        if isinstance(workflow_json, list) and any(
            n.get("type") in ["tab", "inject", "debug", "function", "http request"]
            for n in workflow_json if isinstance(n, dict)
        ):
            return WorkflowPlatform.NODE_RED
        
        # Home Assistant detection
        if "automation" in workflow_json or (
            isinstance(workflow_json, dict) and 
            any(k in workflow_json for k in ["triggers", "trigger", "conditions", "actions"])
        ):
            return WorkflowPlatform.HOME_ASSISTANT
        
        # Make.com / Integromat detection
        if "flow" in workflow_json and "modules" in workflow_json.get("flow", {}):
            return WorkflowPlatform.MAKE
        
        # Activepieces detection
        if "trigger" in workflow_json and "version" in workflow_json:
            return WorkflowPlatform.ACTIVEPIECES
        
        # Windmill detection
        if "value" in workflow_json and "modules" in workflow_json.get("value", {}):
            return WorkflowPlatform.WINDMILL
        
        # Pipedream detection
        if "steps" in workflow_json and any(
            s.get("namespace") for s in workflow_json.get("steps", [])
            if isinstance(s, dict)
        ):
            return WorkflowPlatform.PIPEDREAM
        
        # ComfyUI detection (check last as it's the most generic)
        if isinstance(workflow_json, dict):
            # API format
            first_key = next(iter(workflow_json), None)
            if first_key and first_key.isdigit():
                first_node = workflow_json.get(first_key, {})
                if "class_type" in first_node:
                    return WorkflowPlatform.COMFYUI
            # UI format
            if "nodes" in workflow_json and "links" in workflow_json:
                nodes = workflow_json.get("nodes", [])
                if nodes and isinstance(nodes, list) and "type" in nodes[0]:
                    if any("CLIP" in str(n.get("type", "")) or "KSampler" in str(n.get("type", "")) 
                           for n in nodes):
                        return WorkflowPlatform.COMFYUI
        
        return WorkflowPlatform.UNKNOWN
    
    def parse_workflow(self, workflow_json: Dict) -> WorkflowPlatform:
        """Parse workflow and return detected platform"""
        self.platform = self.detect_platform(workflow_json)
        
        if self.platform == WorkflowPlatform.N8N:
            self._parse_n8n(workflow_json)
        elif self.platform == WorkflowPlatform.NODE_RED:
            self._parse_node_red(workflow_json)
        elif self.platform == WorkflowPlatform.HOME_ASSISTANT:
            self._parse_home_assistant(workflow_json)
        elif self.platform == WorkflowPlatform.MAKE:
            self._parse_make(workflow_json)
        elif self.platform == WorkflowPlatform.ACTIVEPIECES:
            self._parse_activepieces(workflow_json)
        elif self.platform == WorkflowPlatform.WINDMILL:
            self._parse_windmill(workflow_json)
        elif self.platform == WorkflowPlatform.PIPEDREAM:
            self._parse_pipedream(workflow_json)
        elif self.platform == WorkflowPlatform.COMFYUI:
            # Use the dedicated ComfyUI converter for better handling
            from comfyui_converter import ComfyUIConverter
            converter = ComfyUIConverter()
            converter.parse_workflow(workflow_json)
            # Convert ComfyUI nodes to our universal format
            for node_id, node in converter.nodes.items():
                self.nodes[node_id] = WorkflowNode(
                    id=node_id,
                    type=node.our_type or "unknown",
                    name=node.class_type,
                    platform_type=node.class_type,
                    inputs=node.inputs,
                    config=node.inputs,
                    position=(0, 0)  # ComfyNode doesn't store position
                )
        
        return self.platform
    
    # ==================== N8N Parser ====================
    def _parse_n8n(self, workflow_json: Dict):
        """Parse n8n workflow JSON"""
        self.metadata = {
            "name": workflow_json.get("name", "Imported n8n Workflow"),
            "id": workflow_json.get("id"),
            "active": workflow_json.get("active", False),
            "settings": workflow_json.get("settings", {})
        }
        
        nodes = workflow_json.get("nodes", [])
        connections = workflow_json.get("connections", {})
        
        for node in nodes:
            node_id = node.get("id", str(len(self.nodes)))
            
            self.nodes[node_id] = WorkflowNode(
                id=node_id,
                type=self._map_n8n_type(node.get("type", "")),
                name=node.get("name", "Unnamed"),
                platform_type=node.get("type", ""),
                inputs=node.get("parameters", {}),
                config=node.get("parameters", {}),
                position=(
                    node.get("position", [0, 0])[0],
                    node.get("position", [0, 0])[1]
                )
            )
        
        # Parse connections
        for source_name, targets in connections.items():
            source_node = next((n for n in self.nodes.values() if n.name == source_name), None)
            if source_node and "main" in targets:
                for output_connections in targets["main"]:
                    for conn in output_connections:
                        target_name = conn.get("node")
                        target_node = next((n for n in self.nodes.values() if n.name == target_name), None)
                        if target_node:
                            source_node.connections.append(target_node.id)
    
    def _map_n8n_type(self, n8n_type: str) -> str:
        """Map n8n node types to our categories"""
        type_lower = n8n_type.lower()
        
        # Triggers
        if "trigger" in type_lower:
            return "trigger"
        
        # HTTP/API
        if "http" in type_lower or "webhook" in type_lower:
            return "api_request"
        
        # AI/ML
        if any(x in type_lower for x in ["openai", "anthropic", "gemini", "claude", "gpt"]):
            return "ai_generate"
        
        # Social Media
        if any(x in type_lower for x in ["twitter", "instagram", "facebook", "linkedin", "slack"]):
            return "social_media"
        
        # Email
        if any(x in type_lower for x in ["email", "gmail", "smtp"]):
            return "email"
        
        # Database
        if any(x in type_lower for x in ["postgres", "mysql", "mongodb", "database", "sql"]):
            return "database"
        
        # File operations
        if any(x in type_lower for x in ["file", "drive", "dropbox", "s3"]):
            return "file_storage"
        
        # Control flow
        if any(x in type_lower for x in ["if", "switch", "merge", "split"]):
            return "logic"
        
        # Code
        if any(x in type_lower for x in ["code", "function", "javascript"]):
            return "code"
        
        return "action"
    
    # ==================== Node-RED Parser ====================
    def _parse_node_red(self, workflow_json: List):
        """Parse Node-RED flow JSON"""
        if not isinstance(workflow_json, list):
            workflow_json = [workflow_json]
        
        # Node-RED exports as a flat list of nodes
        for node in workflow_json:
            if not isinstance(node, dict):
                continue
            
            node_id = node.get("id", str(len(self.nodes)))
            node_type = node.get("type", "unknown")
            
            # Skip tab nodes (they represent flow tabs)
            if node_type == "tab":
                self.metadata["name"] = node.get("label", "Node-RED Flow")
                continue
            
            self.nodes[node_id] = WorkflowNode(
                id=node_id,
                type=self._map_node_red_type(node_type),
                name=node.get("name", node_type),
                platform_type=node_type,
                inputs=node,
                config=node,
                position=(node.get("x", 0), node.get("y", 0)),
                connections=node.get("wires", [[]])[0] if node.get("wires") else []
            )
    
    def _map_node_red_type(self, node_type: str) -> str:
        """Map Node-RED node types"""
        type_lower = node_type.lower()
        
        if type_lower in ["inject", "trigger"]:
            return "trigger"
        elif type_lower in ["http request", "http in", "http response"]:
            return "api_request"
        elif type_lower in ["function", "template"]:
            return "code"
        elif type_lower == "debug":
            return "output"
        elif type_lower in ["switch", "change"]:
            return "logic"
        elif type_lower in ["mqtt in", "mqtt out"]:
            return "messaging"
        elif type_lower in ["file", "file in"]:
            return "file_storage"
        elif "email" in type_lower:
            return "email"
        
        return "action"
    
    # ==================== Home Assistant Parser ====================
    def _parse_home_assistant(self, workflow_json: Dict):
        """Parse Home Assistant automation YAML/JSON"""
        # Handle both single automation and list of automations
        automations = []
        
        if isinstance(workflow_json, list):
            automations = workflow_json
        elif "automation" in workflow_json:
            automations = workflow_json["automation"]
            if not isinstance(automations, list):
                automations = [automations]
        else:
            automations = [workflow_json]
        
        step_id = 0
        for auto in automations:
            if not isinstance(auto, dict):
                continue
            
            self.metadata["name"] = auto.get("alias", "Home Assistant Automation")
            self.metadata["id"] = auto.get("id")
            
            # Parse triggers
            triggers = auto.get("triggers", auto.get("trigger", []))
            if not isinstance(triggers, list):
                triggers = [triggers]
            
            for trigger in triggers:
                if not isinstance(trigger, dict):
                    continue
                step_id += 1
                self.nodes[str(step_id)] = WorkflowNode(
                    id=str(step_id),
                    type="trigger",
                    name=f"Trigger: {trigger.get('trigger', trigger.get('platform', 'unknown'))}",
                    platform_type=trigger.get("trigger", trigger.get("platform", "unknown")),
                    config=trigger
                )
            
            # Parse conditions
            conditions = auto.get("conditions", auto.get("condition", []))
            if not isinstance(conditions, list):
                conditions = [conditions]
            
            for condition in conditions:
                if not isinstance(condition, dict):
                    continue
                step_id += 1
                self.nodes[str(step_id)] = WorkflowNode(
                    id=str(step_id),
                    type="condition",
                    name=f"Condition: {condition.get('condition', 'unknown')}",
                    platform_type=condition.get("condition", "unknown"),
                    config=condition
                )
            
            # Parse actions
            actions = auto.get("actions", auto.get("action", []))
            if not isinstance(actions, list):
                actions = [actions]
            
            for action in actions:
                if not isinstance(action, dict):
                    continue
                step_id += 1
                action_type = action.get("action", action.get("service", "unknown"))
                self.nodes[str(step_id)] = WorkflowNode(
                    id=str(step_id),
                    type=self._map_ha_action(action_type),
                    name=f"Action: {action_type}",
                    platform_type=action_type,
                    config=action
                )
    
    def _map_ha_action(self, action_type: str) -> str:
        """Map Home Assistant action types"""
        if not action_type:
            return "action"
        
        action_lower = action_type.lower()
        
        if "light" in action_lower:
            return "smart_light"
        elif "switch" in action_lower:
            return "smart_switch"
        elif "notify" in action_lower:
            return "notification"
        elif "media_player" in action_lower:
            return "media"
        elif "climate" in action_lower:
            return "climate"
        elif "script" in action_lower:
            return "script"
        elif "scene" in action_lower:
            return "scene"
        
        return "action"
    
    # ==================== Make.com (Integromat) Parser ====================
    def _parse_make(self, workflow_json: Dict):
        """Parse Make.com scenario JSON"""
        flow = workflow_json.get("flow", workflow_json)
        
        self.metadata = {
            "name": workflow_json.get("name", "Make.com Scenario"),
            "scheduling": workflow_json.get("scheduling", {})
        }
        
        modules = flow.get("modules", [])
        
        for idx, module in enumerate(modules):
            module_id = str(module.get("id", idx))
            
            self.nodes[module_id] = WorkflowNode(
                id=module_id,
                type=self._map_make_type(module),
                name=module.get("name", module.get("module", "Unknown")),
                platform_type=module.get("module", "unknown"),
                config=module.get("parameters", {}),
                inputs=module.get("mapper", {})
            )
    
    def _map_make_type(self, module: Dict) -> str:
        """Map Make.com module types"""
        module_name = module.get("module", "").lower()
        
        if "trigger" in module_name or module.get("trigger"):
            return "trigger"
        elif any(x in module_name for x in ["http", "webhook", "api"]):
            return "api_request"
        elif any(x in module_name for x in ["openai", "gpt", "ai"]):
            return "ai_generate"
        elif any(x in module_name for x in ["gmail", "email", "sendgrid"]):
            return "email"
        elif any(x in module_name for x in ["google", "drive", "sheets"]):
            return "google_integration"
        elif any(x in module_name for x in ["slack", "discord", "teams"]):
            return "messaging"
        elif "router" in module_name:
            return "logic"
        
        return "action"
    
    # ==================== Activepieces Parser ====================
    def _parse_activepieces(self, workflow_json: Dict):
        """Parse Activepieces workflow JSON"""
        self.metadata = {
            "name": workflow_json.get("displayName", "Activepieces Flow"),
            "version": workflow_json.get("version")
        }
        
        # Parse trigger
        trigger = workflow_json.get("trigger", {})
        if trigger:
            self.nodes["trigger"] = WorkflowNode(
                id="trigger",
                type="trigger",
                name=trigger.get("displayName", "Trigger"),
                platform_type=trigger.get("type", "unknown"),
                config=trigger.get("settings", {})
            )
        
        # Parse actions (they can be nested)
        self._parse_activepieces_actions(workflow_json.get("actions", []))
    
    def _parse_activepieces_actions(self, actions: List, parent_id: str = "trigger"):
        """Recursively parse Activepieces actions"""
        for idx, action in enumerate(actions):
            if not isinstance(action, dict):
                continue
            
            action_id = action.get("name", f"action_{idx}")
            
            self.nodes[action_id] = WorkflowNode(
                id=action_id,
                type=self._map_activepieces_type(action),
                name=action.get("displayName", "Action"),
                platform_type=action.get("type", "unknown"),
                config=action.get("settings", {}),
                connections=[parent_id]
            )
            
            # Handle nested actions (branches, loops)
            if "onSuccess" in action:
                self._parse_activepieces_actions(action["onSuccess"], action_id)
    
    def _map_activepieces_type(self, action: Dict) -> str:
        """Map Activepieces action types"""
        action_type = action.get("type", "").lower()
        
        if "trigger" in action_type:
            return "trigger"
        elif "http" in action_type or "webhook" in action_type:
            return "api_request"
        elif "openai" in action_type or "ai" in action_type:
            return "ai_generate"
        elif "branch" in action_type or "condition" in action_type:
            return "logic"
        elif "loop" in action_type:
            return "loop"
        elif "code" in action_type:
            return "code"
        
        return "action"
    
    # ==================== Windmill Parser ====================
    def _parse_windmill(self, workflow_json: Dict):
        """Parse Windmill workflow JSON"""
        value = workflow_json.get("value", workflow_json)
        
        self.metadata = {
            "name": workflow_json.get("path", "Windmill Flow"),
            "description": workflow_json.get("summary", "")
        }
        
        modules = value.get("modules", [])
        
        for idx, module in enumerate(modules):
            module_id = module.get("id", str(idx))
            
            # Windmill modules can be scripts, flows, or special modules
            value_content = module.get("value", {})
            module_type = value_content.get("type", "script")
            
            self.nodes[module_id] = WorkflowNode(
                id=module_id,
                type=self._map_windmill_type(module_type, value_content),
                name=module.get("summary", module_id),
                platform_type=module_type,
                config=value_content,
                inputs=value_content.get("input_transforms", {})
            )
    
    def _map_windmill_type(self, module_type: str, value: Dict) -> str:
        """Map Windmill module types"""
        if module_type == "script":
            return "code"
        elif module_type == "flow":
            return "subflow"
        elif module_type == "branchone" or module_type == "branchall":
            return "logic"
        elif module_type == "forloopflow":
            return "loop"
        elif module_type == "rawscript":
            lang = value.get("language", "")
            if lang == "python3":
                return "python_code"
            elif lang in ["deno", "bun"]:
                return "javascript_code"
            return "code"
        
        return "action"
    
    # ==================== Pipedream Parser ====================
    def _parse_pipedream(self, workflow_json: Dict):
        """Parse Pipedream workflow JSON"""
        self.metadata = {
            "name": workflow_json.get("name", "Pipedream Workflow"),
            "description": workflow_json.get("description", "")
        }
        
        # Parse trigger
        trigger = workflow_json.get("trigger", {})
        if trigger:
            self.nodes["trigger"] = WorkflowNode(
                id="trigger",
                type="trigger",
                name=trigger.get("name", "Trigger"),
                platform_type=trigger.get("type", "unknown"),
                config=trigger
            )
        
        # Parse steps
        steps = workflow_json.get("steps", [])
        for idx, step in enumerate(steps):
            step_id = step.get("key", str(idx))
            
            self.nodes[step_id] = WorkflowNode(
                id=step_id,
                type=self._map_pipedream_type(step),
                name=step.get("name", step_id),
                platform_type=step.get("namespace", "unknown"),
                config=step.get("props", {}),
                inputs=step.get("props", {})
            )
    
    def _map_pipedream_type(self, step: Dict) -> str:
        """Map Pipedream step types"""
        namespace = step.get("namespace", "").lower()
        
        if "http" in namespace:
            return "api_request"
        elif "code" in namespace or step.get("code"):
            return "code"
        elif any(x in namespace for x in ["slack", "discord", "twitter"]):
            return "social_media"
        elif "openai" in namespace:
            return "ai_generate"
        elif any(x in namespace for x in ["google", "sheets", "drive"]):
            return "google_integration"
        elif "email" in namespace:
            return "email"
        
        return "action"
    
    # ==================== Conversion to Our Format ====================
    def convert_to_our_format(self) -> Dict:
        """Convert parsed workflow to our app's format"""
        steps = []
        step_id = 0
        
        # Sort nodes by connections (try to maintain execution order)
        sorted_nodes = self._topological_sort()
        
        for node in sorted_nodes:
            step_id += 1
            step = self._convert_node_to_step(node, step_id)
            if step:
                steps.append(step)
        
        return {
            "steps": steps,
            "schedule": self._extract_schedule(),
            "outputs": [],
            "source": self.platform.value,
            "metadata": self.metadata
        }
    
    def _topological_sort(self) -> List[WorkflowNode]:
        """Sort nodes in execution order"""
        # Simple implementation - triggers first, then by ID
        triggers = [n for n in self.nodes.values() if n.type == "trigger"]
        conditions = [n for n in self.nodes.values() if n.type == "condition"]
        others = [n for n in self.nodes.values() if n.type not in ["trigger", "condition"]]
        
        return triggers + conditions + others
    
    def _convert_node_to_step(self, node: WorkflowNode, step_id: int) -> Optional[Dict]:
        """Convert a universal node to our step format"""
        
        # Map node types to our step types
        type_mapping = {
            "trigger": ("⏱️ Scheduling", "Schedule Trigger"),
            "api_request": ("📤 Distribution", "API Request"),
            "ai_generate": ("🎨 AI Generation", "Generate Image (AI)"),
            "code": ("🔄 Logic", "Custom Code"),
            "logic": ("🔄 Logic", "Conditional Branch"),
            "loop": ("🔄 Logic", "Loop/Iterate"),
            "email": ("📤 Distribution", "Send Email"),
            "social_media": ("📤 Distribution", "Post to Twitter"),
            "messaging": ("📤 Distribution", "Send Notification"),
            "file_storage": ("📤 Distribution", "Save to Folder"),
            "notification": ("📤 Distribution", "Send Notification"),
            "database": ("🔄 Logic", "Database Query"),
            "smart_light": ("🏠 Smart Home", "Control Light"),
            "smart_switch": ("🏠 Smart Home", "Control Switch"),
            "condition": ("🔄 Logic", "Conditional Branch"),
            "output": ("📤 Distribution", "Save to Folder"),
            "action": ("🔄 Logic", "Custom Action"),
        }
        
        category, step_type = type_mapping.get(node.type, ("🔄 Logic", "Custom Action"))
        
        # Build config based on node data
        config = {}
        
        # Extract relevant config fields
        if node.type == "ai_generate":
            config = {
                "model": "prunaai/flux-fast",
                "prompt": self._extract_prompt(node)
            }
        elif node.type in ["email", "notification"]:
            config = {
                "to": node.config.get("to", node.config.get("recipient", "")),
                "subject": node.config.get("subject", ""),
                "body": node.config.get("body", node.config.get("message", ""))
            }
        elif node.type == "api_request":
            config = {
                "url": node.config.get("url", ""),
                "method": node.config.get("method", "GET"),
                "headers": node.config.get("headers", {}),
                "body": node.config.get("body", "")
            }
        elif node.type == "social_media":
            config = {
                "platform": self._detect_social_platform(node),
                "message": node.config.get("text", node.config.get("message", "")),
                "attach_media": True
            }
        else:
            # Copy relevant config
            config = {
                k: v for k, v in node.config.items()
                if k not in ["id", "type", "position", "wires", "z"]
                and not k.startswith("_")
            }
        
        return {
            "id": step_id,
            "category": category,
            "type": step_type,
            "config": config,
            "enabled": True,
            "description": f"{node.name} (from {self.platform.value})",
            "original_type": node.platform_type
        }
    
    def _extract_prompt(self, node: WorkflowNode) -> str:
        """Extract prompt from various config formats"""
        possible_keys = ["prompt", "text", "message", "content", "input"]
        
        for key in possible_keys:
            if key in node.config:
                return str(node.config[key])
        
        return ""
    
    def _detect_social_platform(self, node: WorkflowNode) -> str:
        """Detect which social platform a node targets"""
        type_lower = node.platform_type.lower()
        
        if "twitter" in type_lower or "tweet" in type_lower:
            return "twitter"
        elif "instagram" in type_lower:
            return "instagram"
        elif "facebook" in type_lower:
            return "facebook"
        elif "linkedin" in type_lower:
            return "linkedin"
        elif "slack" in type_lower:
            return "slack"
        elif "discord" in type_lower:
            return "discord"
        
        return "social"
    
    def _extract_schedule(self) -> Optional[Dict]:
        """Extract scheduling info from metadata"""
        if "scheduling" in self.metadata:
            return self.metadata["scheduling"]
        
        # Look for cron patterns in trigger nodes
        for node in self.nodes.values():
            if node.type == "trigger":
                if "cron" in node.config:
                    return {"type": "cron", "pattern": node.config["cron"]}
                if "interval" in node.config:
                    return {"type": "interval", "value": node.config["interval"]}
        
        return None


def analyze_workflow(workflow_json: Dict) -> Dict:
    """Analyze a workflow and return platform info and summary"""
    converter = UniversalWorkflowConverter()
    platform = converter.parse_workflow(workflow_json)
    
    return {
        "platform": platform.value,
        "platform_display": _get_platform_display_name(platform),
        "node_count": len(converter.nodes),
        "nodes": [
            {
                "id": n.id,
                "type": n.type,
                "name": n.name,
                "platform_type": n.platform_type
            }
            for n in converter.nodes.values()
        ],
        "metadata": converter.metadata,
        "summary": _generate_summary(converter)
    }


def convert_workflow(workflow_json: Dict) -> Tuple[Dict, Dict]:
    """
    Convert a workflow from any supported platform to our format.
    Returns (converted_workflow, analysis_info)
    """
    converter = UniversalWorkflowConverter()
    platform = converter.parse_workflow(workflow_json)
    
    if platform == WorkflowPlatform.COMFYUI:
        # Use dedicated ComfyUI converter for better handling
        from comfyui_converter import convert_comfyui_workflow
        return convert_comfyui_workflow(workflow_json)
    
    analysis = analyze_workflow(workflow_json)
    converted = converter.convert_to_our_format()
    
    return converted, analysis


def _get_platform_display_name(platform: WorkflowPlatform) -> str:
    """Get display name for platform"""
    names = {
        WorkflowPlatform.COMFYUI: "ComfyUI (AI Image Generation)",
        WorkflowPlatform.N8N: "n8n (Automation)",
        WorkflowPlatform.NODE_RED: "Node-RED (IoT)",
        WorkflowPlatform.HOME_ASSISTANT: "Home Assistant (Smart Home)",
        WorkflowPlatform.MAKE: "Make.com / Integromat",
        WorkflowPlatform.ACTIVEPIECES: "Activepieces",
        WorkflowPlatform.WINDMILL: "Windmill",
        WorkflowPlatform.PIPEDREAM: "Pipedream",
        WorkflowPlatform.UNKNOWN: "Unknown Platform"
    }
    return names.get(platform, "Unknown")


def _generate_summary(converter: UniversalWorkflowConverter) -> List[str]:
    """Generate summary points about the workflow"""
    summary = []
    
    summary.append(f"Platform: {_get_platform_display_name(converter.platform)}")
    summary.append(f"Total nodes: {len(converter.nodes)}")
    
    # Count node types
    type_counts = {}
    for node in converter.nodes.values():
        type_counts[node.type] = type_counts.get(node.type, 0) + 1
    
    if type_counts:
        type_summary = ", ".join(f"{count} {t}" for t, count in type_counts.items())
        summary.append(f"Node types: {type_summary}")
    
    # Workflow name
    if "name" in converter.metadata:
        summary.append(f"Name: {converter.metadata['name']}")
    
    return summary


# Supported platforms info for UI
SUPPORTED_PLATFORMS = [
    {
        "id": "comfyui",
        "name": "ComfyUI",
        "description": "AI image generation workflows from ComfyUI or comfyworkflows.com",
        "icon": "🎨",
        "export_help": "In ComfyUI: Menu → Export (API) or Save workflow"
    },
    {
        "id": "n8n",
        "name": "n8n",
        "description": "General automation workflows from n8n.io",
        "icon": "⚡",
        "export_help": "In n8n: Menu → Download workflow JSON"
    },
    {
        "id": "node-red",
        "name": "Node-RED",
        "description": "IoT and event-driven automation flows",
        "icon": "🔴",
        "export_help": "In Node-RED: Menu → Export → Clipboard/Download"
    },
    {
        "id": "home-assistant",
        "name": "Home Assistant",
        "description": "Smart home automation (YAML/JSON)",
        "icon": "🏠",
        "export_help": "Copy automation YAML from Home Assistant config"
    },
    {
        "id": "make",
        "name": "Make.com (Integromat)",
        "description": "Business automation scenarios",
        "icon": "🔧",
        "export_help": "In Make: Scenario → Export blueprint"
    },
    {
        "id": "activepieces",
        "name": "Activepieces",
        "description": "Open-source automation platform",
        "icon": "🧩",
        "export_help": "In Activepieces: Flow → Export"
    },
    {
        "id": "windmill",
        "name": "Windmill",
        "description": "Developer-focused workflow automation",
        "icon": "💨",
        "export_help": "In Windmill: Flow → Export JSON"
    },
    {
        "id": "pipedream",
        "name": "Pipedream",
        "description": "Developer workflow platform",
        "icon": "🚰",
        "export_help": "In Pipedream: Workflow → Export"
    }
]
