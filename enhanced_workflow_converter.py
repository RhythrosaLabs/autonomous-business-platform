"""
Enhanced Universal Workflow Converter v2.0

Hyper-intelligent workflow converter that:
1. Semantic understanding of workflow intent across all platforms
2. Deep node analysis and capability mapping
3. Intelligent step consolidation
4. Context-aware parameter extraction
5. Workflow optimization suggestions
6. Cross-platform feature mapping
"""

import json
import logging
import re
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

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
    ZAPIER = "zapier"
    IFTTT = "ifttt"
    POWER_AUTOMATE = "power-automate"
    UNKNOWN = "unknown"


class StepCategory(Enum):
    """Universal step categories"""
    AI_GENERATION = "🎨 AI Generation"
    AI_EDITING = "✏️ AI Editing"
    DISTRIBUTION = "📤 Distribution"
    DATA_PROCESSING = "📊 Data Processing"
    FILE_OPERATIONS = "📁 File Operations"
    COMMUNICATION = "📧 Communication"
    TRIGGERS = "⚡ Triggers"
    LOGIC = "🔀 Logic"
    UTILITIES = "🔧 Utilities"


@dataclass
class UniversalNode:
    """Universal node representation with rich metadata"""
    id: str
    original_type: str
    platform: WorkflowPlatform
    name: str
    description: str = ""
    
    # Semantic understanding
    intent: str = ""  # What this node is trying to do
    capability: str = ""  # What capability it provides
    category: StepCategory = StepCategory.UTILITIES
    
    # Configuration
    inputs: Dict = field(default_factory=dict)
    outputs: Dict = field(default_factory=dict)
    config: Dict = field(default_factory=dict)
    
    # Connections
    connections_in: List[str] = field(default_factory=list)
    connections_out: List[str] = field(default_factory=list)
    
    # Position for visual layout
    position: Tuple[int, int] = (0, 0)
    
    # Conversion hints
    our_step_type: str = ""
    requires_input: bool = False
    produces_output: bool = False
    output_type: str = ""  # image, video, text, data, file


@dataclass
class WorkflowAnalysis:
    """Comprehensive workflow analysis"""
    platform: WorkflowPlatform
    node_count: int = 0
    complexity_score: float = 0.0
    
    # Detected capabilities
    has_ai_generation: bool = False
    has_image_editing: bool = False
    has_video_generation: bool = False
    has_audio_generation: bool = False
    has_distribution: bool = False
    has_data_processing: bool = False
    has_file_operations: bool = False
    has_api_calls: bool = False
    has_conditional_logic: bool = False
    has_loops: bool = False
    has_scheduling: bool = False
    
    # Extracted data
    prompts: List[str] = field(default_factory=list)
    models_referenced: List[str] = field(default_factory=list)
    api_endpoints: List[str] = field(default_factory=list)
    file_paths: List[str] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    
    # Quality metrics
    optimization_suggestions: List[str] = field(default_factory=list)
    potential_issues: List[str] = field(default_factory=list)
    
    # Summary
    description: str = ""
    estimated_execution_time: float = 0.0


# Platform-specific node type mappings
PLATFORM_NODE_MAPPINGS = {
    # n8n node types
    "n8n": {
        # AI/ML
        "n8n-nodes-base.openAi": {"capability": "ai_generation", "our_type": "Generate Image (AI)", "category": StepCategory.AI_GENERATION},
        "n8n-nodes-base.anthropic": {"capability": "text_generation", "our_type": "Generate Text", "category": StepCategory.AI_GENERATION},
        "n8n-nodes-base.huggingFace": {"capability": "ai_inference", "our_type": "Generate Image (AI)", "category": StepCategory.AI_GENERATION},
        "@n8n/n8n-nodes-langchain.*": {"capability": "ai_agent", "our_type": "AI Agent", "category": StepCategory.AI_GENERATION},
        
        # Social/Distribution
        "n8n-nodes-base.twitter": {"capability": "social_post", "our_type": "Post to Twitter", "category": StepCategory.DISTRIBUTION},
        "n8n-nodes-base.instagram": {"capability": "social_post", "our_type": "Post to Instagram", "category": StepCategory.DISTRIBUTION},
        "n8n-nodes-base.facebook": {"capability": "social_post", "our_type": "Post to Facebook", "category": StepCategory.DISTRIBUTION},
        "n8n-nodes-base.linkedin": {"capability": "social_post", "our_type": "Post to LinkedIn", "category": StepCategory.DISTRIBUTION},
        "n8n-nodes-base.youtube": {"capability": "video_upload", "our_type": "Upload to YouTube", "category": StepCategory.DISTRIBUTION},
        
        # Communication
        "n8n-nodes-base.gmail": {"capability": "email", "our_type": "Send Email", "category": StepCategory.COMMUNICATION},
        "n8n-nodes-base.slack": {"capability": "messaging", "our_type": "Send Slack Message", "category": StepCategory.COMMUNICATION},
        "n8n-nodes-base.telegram": {"capability": "messaging", "our_type": "Send Telegram Message", "category": StepCategory.COMMUNICATION},
        "n8n-nodes-base.discord": {"capability": "messaging", "our_type": "Send Discord Message", "category": StepCategory.COMMUNICATION},
        
        # File/Storage
        "n8n-nodes-base.googleDrive": {"capability": "file_storage", "our_type": "Save to Cloud", "category": StepCategory.FILE_OPERATIONS},
        "n8n-nodes-base.dropbox": {"capability": "file_storage", "our_type": "Save to Cloud", "category": StepCategory.FILE_OPERATIONS},
        "n8n-nodes-base.ftp": {"capability": "file_transfer", "our_type": "Upload File", "category": StepCategory.FILE_OPERATIONS},
        "n8n-nodes-base.readWriteFile": {"capability": "file_io", "our_type": "Save to Folder", "category": StepCategory.FILE_OPERATIONS},
        
        # Data
        "n8n-nodes-base.spreadsheetFile": {"capability": "spreadsheet", "our_type": "Process Spreadsheet", "category": StepCategory.DATA_PROCESSING},
        "n8n-nodes-base.googleSheets": {"capability": "spreadsheet", "our_type": "Update Spreadsheet", "category": StepCategory.DATA_PROCESSING},
        "n8n-nodes-base.airtable": {"capability": "database", "our_type": "Update Database", "category": StepCategory.DATA_PROCESSING},
        
        # E-commerce
        "n8n-nodes-base.shopify": {"capability": "ecommerce", "our_type": "Upload to Shopify", "category": StepCategory.DISTRIBUTION},
        "n8n-nodes-base.wooCommerce": {"capability": "ecommerce", "our_type": "Upload to WooCommerce", "category": StepCategory.DISTRIBUTION},
        
        # Triggers
        "n8n-nodes-base.schedule": {"capability": "trigger", "our_type": "Schedule", "category": StepCategory.TRIGGERS},
        "n8n-nodes-base.webhook": {"capability": "trigger", "our_type": "Webhook Trigger", "category": StepCategory.TRIGGERS},
        "n8n-nodes-base.manualTrigger": {"capability": "trigger", "our_type": "Manual Start", "category": StepCategory.TRIGGERS},
        
        # Logic
        "n8n-nodes-base.if": {"capability": "conditional", "our_type": "Conditional Branch", "category": StepCategory.LOGIC},
        "n8n-nodes-base.switch": {"capability": "conditional", "our_type": "Switch", "category": StepCategory.LOGIC},
        "n8n-nodes-base.merge": {"capability": "merge", "our_type": "Merge", "category": StepCategory.LOGIC},
        "n8n-nodes-base.splitInBatches": {"capability": "loop", "our_type": "Loop", "category": StepCategory.LOGIC},
        
        # API
        "n8n-nodes-base.httpRequest": {"capability": "api_call", "our_type": "API Call", "category": StepCategory.UTILITIES},
    },
    
    # Node-RED node types  
    "node-red": {
        "inject": {"capability": "trigger", "our_type": "Manual Start", "category": StepCategory.TRIGGERS},
        "http request": {"capability": "api_call", "our_type": "API Call", "category": StepCategory.UTILITIES},
        "http in": {"capability": "webhook", "our_type": "Webhook Trigger", "category": StepCategory.TRIGGERS},
        "mqtt in": {"capability": "trigger", "our_type": "MQTT Trigger", "category": StepCategory.TRIGGERS},
        "mqtt out": {"capability": "publish", "our_type": "MQTT Publish", "category": StepCategory.DISTRIBUTION},
        "function": {"capability": "code", "our_type": "Custom Code", "category": StepCategory.UTILITIES},
        "change": {"capability": "transform", "our_type": "Transform Data", "category": StepCategory.DATA_PROCESSING},
        "switch": {"capability": "conditional", "our_type": "Conditional Branch", "category": StepCategory.LOGIC},
        "file": {"capability": "file_io", "our_type": "Save to Folder", "category": StepCategory.FILE_OPERATIONS},
        "email": {"capability": "email", "our_type": "Send Email", "category": StepCategory.COMMUNICATION},
        "debug": {"capability": "debug", "our_type": "Debug", "category": StepCategory.UTILITIES},
    },
    
    # Home Assistant automation
    "home-assistant": {
        "state": {"capability": "trigger", "our_type": "State Change Trigger", "category": StepCategory.TRIGGERS},
        "time": {"capability": "trigger", "our_type": "Schedule", "category": StepCategory.TRIGGERS},
        "event": {"capability": "trigger", "our_type": "Event Trigger", "category": StepCategory.TRIGGERS},
        "sun": {"capability": "trigger", "our_type": "Sun Trigger", "category": StepCategory.TRIGGERS},
        "webhook": {"capability": "webhook", "our_type": "Webhook Trigger", "category": StepCategory.TRIGGERS},
        "service": {"capability": "action", "our_type": "Home Automation Action", "category": StepCategory.UTILITIES},
        "device": {"capability": "action", "our_type": "Device Control", "category": StepCategory.UTILITIES},
        "notification": {"capability": "notification", "our_type": "Send Notification", "category": StepCategory.COMMUNICATION},
    },
    
    # Make.com / Integromat
    "make": {
        "openai:CreateCompletion": {"capability": "ai_generation", "our_type": "Generate Text", "category": StepCategory.AI_GENERATION},
        "openai:GenerateImage": {"capability": "ai_generation", "our_type": "Generate Image (AI)", "category": StepCategory.AI_GENERATION},
        "twitter:CreateTweet": {"capability": "social_post", "our_type": "Post to Twitter", "category": StepCategory.DISTRIBUTION},
        "instagram:CreatePost": {"capability": "social_post", "our_type": "Post to Instagram", "category": StepCategory.DISTRIBUTION},
        "shopify:*": {"capability": "ecommerce", "our_type": "Shopify Action", "category": StepCategory.DISTRIBUTION},
        "http:MakeRequest": {"capability": "api_call", "our_type": "API Call", "category": StepCategory.UTILITIES},
        "google-drive:*": {"capability": "file_storage", "our_type": "Google Drive", "category": StepCategory.FILE_OPERATIONS},
        "router": {"capability": "conditional", "our_type": "Conditional Branch", "category": StepCategory.LOGIC},
        "flow-control:*": {"capability": "flow", "our_type": "Flow Control", "category": StepCategory.LOGIC},
    },
    
    # Activepieces
    "activepieces": {
        "openai": {"capability": "ai_generation", "our_type": "Generate Image (AI)", "category": StepCategory.AI_GENERATION},
        "schedule": {"capability": "trigger", "our_type": "Schedule", "category": StepCategory.TRIGGERS},
        "webhook": {"capability": "webhook", "our_type": "Webhook Trigger", "category": StepCategory.TRIGGERS},
        "http": {"capability": "api_call", "our_type": "API Call", "category": StepCategory.UTILITIES},
        "gmail": {"capability": "email", "our_type": "Send Email", "category": StepCategory.COMMUNICATION},
        "slack": {"capability": "messaging", "our_type": "Send Slack Message", "category": StepCategory.COMMUNICATION},
        "google-sheets": {"capability": "spreadsheet", "our_type": "Update Spreadsheet", "category": StepCategory.DATA_PROCESSING},
        "branch": {"capability": "conditional", "our_type": "Conditional Branch", "category": StepCategory.LOGIC},
        "loop": {"capability": "loop", "our_type": "Loop", "category": StepCategory.LOGIC},
    },
    
    # Pipedream
    "pipedream": {
        "openai": {"capability": "ai_generation", "our_type": "Generate Image (AI)", "category": StepCategory.AI_GENERATION},
        "anthropic": {"capability": "text_generation", "our_type": "Generate Text", "category": StepCategory.AI_GENERATION},
        "twitter": {"capability": "social_post", "our_type": "Post to Twitter", "category": StepCategory.DISTRIBUTION},
        "shopify": {"capability": "ecommerce", "our_type": "Shopify Action", "category": StepCategory.DISTRIBUTION},
        "github": {"capability": "dev_tools", "our_type": "GitHub Action", "category": StepCategory.UTILITIES},
        "$.http": {"capability": "api_call", "our_type": "API Call", "category": StepCategory.UTILITIES},
        "trigger": {"capability": "trigger", "our_type": "Trigger", "category": StepCategory.TRIGGERS},
    },
    
    # Windmill
    "windmill": {
        "script": {"capability": "code", "our_type": "Custom Code", "category": StepCategory.UTILITIES},
        "flow": {"capability": "flow", "our_type": "Sub-workflow", "category": StepCategory.LOGIC},
        "forloop": {"capability": "loop", "our_type": "Loop", "category": StepCategory.LOGIC},
        "branchone": {"capability": "conditional", "our_type": "Conditional Branch", "category": StepCategory.LOGIC},
        "branchall": {"capability": "parallel", "our_type": "Parallel Execution", "category": StepCategory.LOGIC},
    },
}


# Semantic patterns for intent detection
SEMANTIC_PATTERNS = {
    # AI/Generation patterns
    r"(generat|creat|produc|render|synthesiz).*(image|picture|photo|art)": "image_generation",
    r"(generat|creat|produc).*(video|animation|clip)": "video_generation",
    r"(generat|creat|produc).*(music|audio|sound|song)": "audio_generation",
    r"(generat|creat|write).*(text|content|copy|article|post)": "text_generation",
    r"(gpt|openai|anthropic|claude|llm)": "text_generation",
    r"(dall-e|stable.?diffusion|midjourney|flux)": "image_generation",
    
    # Editing patterns
    r"(edit|modif|chang|transform|alter).*(image|photo|picture)": "image_editing",
    r"(upscal|enhanc|improv|increas).*(quality|resolution|detail)": "upscaling",
    r"(remove|delet|eras).*(background|object)": "background_removal",
    r"(inpaint|fill|replac)": "inpainting",
    
    # Distribution patterns
    r"(post|publish|share|upload).*(twitter|x\.com|tweet)": "post_twitter",
    r"(post|publish|share|upload).*(instagram|ig)": "post_instagram",
    r"(post|publish|share|upload).*(facebook|fb)": "post_facebook",
    r"(post|publish|share|upload).*(linkedin)": "post_linkedin",
    r"(post|publish|share|upload).*(youtube)": "upload_youtube",
    r"(upload|push|send).*(shopify)": "upload_shopify",
    r"(upload|push|send).*(printify)": "upload_printify",
    r"(upload|push|send).*(etsy)": "upload_etsy",
    
    # Communication patterns
    r"(send|compose).*(email|mail|gmail)": "send_email",
    r"(send|post).*(slack|message)": "send_slack",
    r"(send|post).*(discord)": "send_discord",
    r"(send|post).*(telegram)": "send_telegram",
    r"(notif|alert)": "send_notification",
    
    # File patterns
    r"(save|write|export|output).*(file|folder|disk|local)": "save_file",
    r"(save|upload).*(drive|cloud|dropbox|s3)": "save_cloud",
    r"(download|fetch|get).*(file|image|video)": "download_file",
    
    # Data patterns
    r"(read|get|fetch).*(spreadsheet|sheet|excel|csv)": "read_spreadsheet",
    r"(write|update|add).*(spreadsheet|sheet|excel|csv)": "write_spreadsheet",
    r"(query|select|get).*(database|db|sql)": "query_database",
    r"(insert|update|add).*(database|db|sql)": "write_database",
    
    # Logic patterns
    r"(if|when|condition|check)": "conditional",
    r"(loop|repeat|iterate|foreach)": "loop",
    r"(wait|delay|sleep|pause)": "delay",
    r"(schedule|cron|timer|every)": "schedule",
}


class EnhancedUniversalConverter:
    """
    Hyper-intelligent workflow converter with deep semantic understanding.
    """
    
    def __init__(self):
        self.nodes: Dict[str, UniversalNode] = {}
        self.platform: WorkflowPlatform = WorkflowPlatform.UNKNOWN
        self.analysis: WorkflowAnalysis = None
        self.execution_order: List[str] = []
    
    def detect_platform(self, workflow_json: Any) -> WorkflowPlatform:
        """Auto-detect workflow platform with high accuracy"""
        
        if isinstance(workflow_json, str):
            try:
                workflow_json = json.loads(workflow_json)
            except:
                return WorkflowPlatform.UNKNOWN
        
        # n8n: has nodes array with n8n-nodes type prefix
        if isinstance(workflow_json, dict):
            if "nodes" in workflow_json:
                nodes = workflow_json.get("nodes", [])
                if isinstance(nodes, list) and nodes:
                    first_node = nodes[0] if nodes else {}
                    
                    # n8n detection
                    if any(n.get("type", "").startswith("n8n-nodes") or 
                           n.get("type", "").startswith("@n8n") for n in nodes):
                        return WorkflowPlatform.N8N
                    
                    # ComfyUI UI format detection
                    if "links" in workflow_json:
                        if any("class_type" in str(n) or "widgets_values" in n for n in nodes):
                            return WorkflowPlatform.COMFYUI
                        # Check for ComfyUI node types
                        if any(n.get("type", "") in ("KSampler", "CLIPTextEncode", "CheckpointLoaderSimple") 
                               for n in nodes):
                            return WorkflowPlatform.COMFYUI
        
        # Node-RED: is array or has array with inject/debug/function nodes
        if isinstance(workflow_json, list):
            if any(n.get("type") in ("inject", "debug", "function", "tab", "http request", "http in", "mqtt in")
                   for n in workflow_json if isinstance(n, dict)):
                return WorkflowPlatform.NODE_RED
        
        # Home Assistant: has triggers/conditions/actions structure
        if isinstance(workflow_json, dict):
            if any(k in workflow_json for k in ["triggers", "trigger", "actions", "action"]):
                if "automation" in workflow_json or "alias" in workflow_json:
                    return WorkflowPlatform.HOME_ASSISTANT
        
        # Make.com: has flow.modules structure
        if isinstance(workflow_json, dict):
            if "flow" in workflow_json and "modules" in workflow_json.get("flow", {}):
                return WorkflowPlatform.MAKE
        
        # Activepieces: has trigger and version fields
        if isinstance(workflow_json, dict):
            if "trigger" in workflow_json and "version" in workflow_json:
                return WorkflowPlatform.ACTIVEPIECES
        
        # Windmill: has value.modules structure
        if isinstance(workflow_json, dict):
            if "value" in workflow_json and "modules" in workflow_json.get("value", {}):
                return WorkflowPlatform.WINDMILL
        
        # Pipedream: has steps with namespace
        if isinstance(workflow_json, dict):
            if "steps" in workflow_json:
                steps = workflow_json.get("steps", [])
                if steps and isinstance(steps, list):
                    if any(isinstance(s, dict) and ("namespace" in s or "props" in s) for s in steps):
                        return WorkflowPlatform.PIPEDREAM
        
        # ComfyUI API format: keys are numbers with class_type
        if isinstance(workflow_json, dict):
            first_key = next(iter(workflow_json), None)
            if first_key and (first_key.isdigit() or str(first_key).isdigit()):
                first_node = workflow_json.get(first_key, {})
                if isinstance(first_node, dict) and "class_type" in first_node:
                    return WorkflowPlatform.COMFYUI
        
        return WorkflowPlatform.UNKNOWN
    
    def convert_workflow(self, workflow_json: Any) -> Tuple[Dict, WorkflowAnalysis]:
        """
        Main conversion method - detects platform and converts to our format.
        
        Returns:
            Tuple of (converted_workflow, analysis)
        """
        self.platform = self.detect_platform(workflow_json)
        
        if self.platform == WorkflowPlatform.COMFYUI:
            return self._convert_comfyui(workflow_json)
        elif self.platform == WorkflowPlatform.N8N:
            return self._convert_n8n(workflow_json)
        elif self.platform == WorkflowPlatform.NODE_RED:
            return self._convert_node_red(workflow_json)
        elif self.platform == WorkflowPlatform.HOME_ASSISTANT:
            return self._convert_home_assistant(workflow_json)
        elif self.platform == WorkflowPlatform.MAKE:
            return self._convert_make(workflow_json)
        elif self.platform == WorkflowPlatform.ACTIVEPIECES:
            return self._convert_activepieces(workflow_json)
        elif self.platform == WorkflowPlatform.WINDMILL:
            return self._convert_windmill(workflow_json)
        elif self.platform == WorkflowPlatform.PIPEDREAM:
            return self._convert_pipedream(workflow_json)
        else:
            return self._convert_unknown(workflow_json)
    
    def _convert_comfyui(self, workflow_json: Dict) -> Tuple[Dict, WorkflowAnalysis]:
        """Convert ComfyUI workflow using dedicated converter"""
        from comfyui_converter import ComfyUIConverter, convert_comfyui_workflow
        
        our_workflow, info = convert_comfyui_workflow(workflow_json)
        
        # Create analysis
        analysis = WorkflowAnalysis(
            platform=WorkflowPlatform.COMFYUI,
            node_count=info.get("node_count", len(workflow_json)),
            has_ai_generation=True,
            has_image_editing=info.get("is_inpainting", False),
            has_video_generation=info.get("is_video", False),
            prompts=[info.get("prompts", {}).get("positive", "")],
            models_referenced=[info.get("model", "")] if info.get("model") else [],
            description=f"ComfyUI workflow with {info.get('node_count', '?')} nodes",
        )
        
        return our_workflow, analysis
    
    def _convert_n8n(self, workflow_json: Dict) -> Tuple[Dict, WorkflowAnalysis]:
        """Convert n8n workflow"""
        nodes = workflow_json.get("nodes", [])
        connections = workflow_json.get("connections", {})
        
        analysis = WorkflowAnalysis(
            platform=WorkflowPlatform.N8N,
            node_count=len(nodes),
        )
        
        steps = []
        step_id = 1
        
        # First pass: parse all nodes
        for node in nodes:
            node_type = node.get("type", "")
            node_name = node.get("name", node_type)
            params = node.get("parameters", {})
            
            # Find matching capability
            mapping = self._find_n8n_mapping(node_type)
            
            # Analyze intent from parameters
            intent = self._analyze_intent(node_name, params)
            
            # Update analysis
            if mapping["capability"] == "ai_generation":
                analysis.has_ai_generation = True
            elif mapping["capability"] == "social_post":
                analysis.has_distribution = True
            elif mapping["capability"] == "trigger":
                analysis.triggers.append(node_name)
            elif mapping["capability"] == "conditional":
                analysis.has_conditional_logic = True
            elif mapping["capability"] == "loop":
                analysis.has_loops = True
            
            # Extract prompts
            for key in ["prompt", "text", "message", "content", "body"]:
                if key in params and params[key]:
                    analysis.prompts.append(str(params[key]))
            
            # Create step if it's an action node (not trigger/logic)
            if mapping["category"] not in [StepCategory.TRIGGERS, StepCategory.LOGIC]:
                step = {
                    "id": step_id,
                    "category": mapping["category"].value,
                    "type": mapping["our_type"],
                    "config": self._extract_config(params, mapping["capability"]),
                    "enabled": True,
                    "description": f"{node_name}: {mapping['capability']}"
                }
                steps.append(step)
                step_id += 1
        
        # Calculate complexity
        analysis.complexity_score = self._calculate_complexity(len(nodes), analysis)
        analysis.description = f"n8n workflow with {len(nodes)} nodes"
        
        return {
            "steps": steps,
            "schedule": self._extract_schedule(workflow_json),
            "outputs": [],
            "source": "n8n",
            "original_workflow": workflow_json,
        }, analysis
    
    def _convert_node_red(self, workflow_json: List) -> Tuple[Dict, WorkflowAnalysis]:
        """Convert Node-RED workflow"""
        nodes = [n for n in workflow_json if isinstance(n, dict) and n.get("type") != "tab"]
        
        analysis = WorkflowAnalysis(
            platform=WorkflowPlatform.NODE_RED,
            node_count=len(nodes),
        )
        
        steps = []
        step_id = 1
        
        for node in nodes:
            node_type = node.get("type", "")
            node_name = node.get("name", node_type)
            
            mapping = PLATFORM_NODE_MAPPINGS.get("node-red", {}).get(node_type, {
                "capability": "unknown",
                "our_type": node_type,
                "category": StepCategory.UTILITIES
            })
            
            # Skip trigger and debug nodes in steps
            if mapping["capability"] in ["trigger", "debug"]:
                if mapping["capability"] == "trigger":
                    analysis.triggers.append(node_name)
                continue
            
            step = {
                "id": step_id,
                "category": mapping["category"].value if hasattr(mapping["category"], "value") else str(mapping["category"]),
                "type": mapping["our_type"],
                "config": {},
                "enabled": True,
                "description": node_name
            }
            steps.append(step)
            step_id += 1
        
        analysis.description = f"Node-RED flow with {len(nodes)} nodes"
        
        return {
            "steps": steps,
            "schedule": None,
            "outputs": [],
            "source": "node-red",
        }, analysis
    
    def _convert_home_assistant(self, workflow_json: Dict) -> Tuple[Dict, WorkflowAnalysis]:
        """Convert Home Assistant automation"""
        analysis = WorkflowAnalysis(
            platform=WorkflowPlatform.HOME_ASSISTANT,
            has_scheduling=True,
        )
        
        triggers = workflow_json.get("triggers", workflow_json.get("trigger", []))
        if not isinstance(triggers, list):
            triggers = [triggers]
        
        actions = workflow_json.get("actions", workflow_json.get("action", []))
        if not isinstance(actions, list):
            actions = [actions]
        
        analysis.node_count = len(triggers) + len(actions)
        
        for trigger in triggers:
            analysis.triggers.append(trigger.get("platform", "unknown"))
        
        steps = []
        for i, action in enumerate(actions, 1):
            action_type = action.get("service", action.get("action", "unknown"))
            
            steps.append({
                "id": i,
                "category": StepCategory.UTILITIES.value,
                "type": "Home Automation Action",
                "config": action,
                "enabled": True,
                "description": f"HA: {action_type}"
            })
        
        analysis.description = f"Home Assistant automation with {len(triggers)} triggers and {len(actions)} actions"
        
        return {
            "steps": steps,
            "schedule": None,
            "outputs": [],
            "source": "home-assistant",
        }, analysis
    
    def _convert_make(self, workflow_json: Dict) -> Tuple[Dict, WorkflowAnalysis]:
        """Convert Make.com (Integromat) workflow"""
        flow = workflow_json.get("flow", {})
        modules = flow.get("modules", [])
        
        analysis = WorkflowAnalysis(
            platform=WorkflowPlatform.MAKE,
            node_count=len(modules),
        )
        
        steps = []
        for i, module in enumerate(modules, 1):
            module_type = module.get("module", "")
            
            # Find mapping
            mapping = None
            for pattern, m in PLATFORM_NODE_MAPPINGS.get("make", {}).items():
                if pattern.endswith("*"):
                    if module_type.startswith(pattern[:-1]):
                        mapping = m
                        break
                elif module_type == pattern:
                    mapping = m
                    break
            
            if not mapping:
                mapping = {"capability": "unknown", "our_type": module_type, "category": StepCategory.UTILITIES}
            
            steps.append({
                "id": i,
                "category": mapping["category"].value if hasattr(mapping["category"], "value") else str(mapping["category"]),
                "type": mapping["our_type"],
                "config": module.get("parameters", {}),
                "enabled": True,
                "description": f"Make: {module_type}"
            })
        
        analysis.description = f"Make.com workflow with {len(modules)} modules"
        
        return {
            "steps": steps,
            "schedule": None,
            "outputs": [],
            "source": "make",
        }, analysis
    
    def _convert_activepieces(self, workflow_json: Dict) -> Tuple[Dict, WorkflowAnalysis]:
        """Convert Activepieces workflow"""
        trigger = workflow_json.get("trigger", {})
        actions = workflow_json.get("actions", {})
        
        analysis = WorkflowAnalysis(
            platform=WorkflowPlatform.ACTIVEPIECES,
            node_count=1 + len(actions),
        )
        
        if trigger:
            analysis.triggers.append(trigger.get("type", "unknown"))
        
        steps = []
        for i, (action_id, action) in enumerate(actions.items(), 1):
            action_type = action.get("type", "")
            
            mapping = PLATFORM_NODE_MAPPINGS.get("activepieces", {}).get(action_type.split(":")[0], {
                "capability": "unknown",
                "our_type": action_type,
                "category": StepCategory.UTILITIES
            })
            
            steps.append({
                "id": i,
                "category": mapping["category"].value if hasattr(mapping["category"], "value") else str(mapping["category"]),
                "type": mapping["our_type"],
                "config": action.get("settings", {}),
                "enabled": True,
                "description": f"Activepieces: {action_type}"
            })
        
        analysis.description = f"Activepieces flow with {len(actions)} actions"
        
        return {
            "steps": steps,
            "schedule": None,
            "outputs": [],
            "source": "activepieces",
        }, analysis
    
    def _convert_windmill(self, workflow_json: Dict) -> Tuple[Dict, WorkflowAnalysis]:
        """Convert Windmill workflow"""
        value = workflow_json.get("value", {})
        modules = value.get("modules", [])
        
        analysis = WorkflowAnalysis(
            platform=WorkflowPlatform.WINDMILL,
            node_count=len(modules),
        )
        
        steps = []
        for i, module in enumerate(modules, 1):
            module_id = module.get("id", "")
            module_type = module.get("type", "script")
            
            mapping = PLATFORM_NODE_MAPPINGS.get("windmill", {}).get(module_type, {
                "capability": "code",
                "our_type": "Custom Code",
                "category": StepCategory.UTILITIES
            })
            
            steps.append({
                "id": i,
                "category": mapping["category"].value if hasattr(mapping["category"], "value") else str(mapping["category"]),
                "type": mapping["our_type"],
                "config": module.get("value", {}),
                "enabled": True,
                "description": f"Windmill: {module_id}"
            })
        
        analysis.description = f"Windmill flow with {len(modules)} modules"
        
        return {
            "steps": steps,
            "schedule": None,
            "outputs": [],
            "source": "windmill",
        }, analysis
    
    def _convert_pipedream(self, workflow_json: Dict) -> Tuple[Dict, WorkflowAnalysis]:
        """Convert Pipedream workflow"""
        steps_list = workflow_json.get("steps", [])
        
        analysis = WorkflowAnalysis(
            platform=WorkflowPlatform.PIPEDREAM,
            node_count=len(steps_list),
        )
        
        steps = []
        for i, step in enumerate(steps_list, 1):
            namespace = step.get("namespace", "")
            
            mapping = PLATFORM_NODE_MAPPINGS.get("pipedream", {}).get(namespace, {
                "capability": "unknown",
                "our_type": namespace or "Custom Step",
                "category": StepCategory.UTILITIES
            })
            
            steps.append({
                "id": i,
                "category": mapping["category"].value if hasattr(mapping["category"], "value") else str(mapping["category"]),
                "type": mapping["our_type"],
                "config": step.get("props", {}),
                "enabled": True,
                "description": f"Pipedream: {namespace}"
            })
        
        analysis.description = f"Pipedream workflow with {len(steps_list)} steps"
        
        return {
            "steps": steps,
            "schedule": None,
            "outputs": [],
            "source": "pipedream",
        }, analysis
    
    def _convert_unknown(self, workflow_json: Any) -> Tuple[Dict, WorkflowAnalysis]:
        """Handle unknown workflow format with best-effort conversion"""
        analysis = WorkflowAnalysis(
            platform=WorkflowPlatform.UNKNOWN,
            description="Unknown workflow format - best-effort conversion",
        )
        
        # Try to extract any useful information
        steps = []
        if isinstance(workflow_json, dict):
            # Look for common patterns
            for key in ["steps", "nodes", "actions", "modules", "tasks"]:
                if key in workflow_json:
                    items = workflow_json[key]
                    if isinstance(items, list):
                        for i, item in enumerate(items, 1):
                            steps.append({
                                "id": i,
                                "category": StepCategory.UTILITIES.value,
                                "type": "Unknown Step",
                                "config": item if isinstance(item, dict) else {"value": item},
                                "enabled": True,
                                "description": f"Imported step {i}"
                            })
                    analysis.node_count = len(items)
                    break
        
        return {
            "steps": steps,
            "schedule": None,
            "outputs": [],
            "source": "unknown",
        }, analysis
    
    # Helper methods
    
    def _find_n8n_mapping(self, node_type: str) -> Dict:
        """Find mapping for n8n node type"""
        mappings = PLATFORM_NODE_MAPPINGS.get("n8n", {})
        
        # Exact match
        if node_type in mappings:
            return mappings[node_type]
        
        # Pattern match (for wildcards)
        for pattern, mapping in mappings.items():
            if pattern.endswith("*"):
                if node_type.startswith(pattern[:-1]):
                    return mapping
        
        # Default
        return {"capability": "unknown", "our_type": node_type, "category": StepCategory.UTILITIES}
    
    def _analyze_intent(self, name: str, params: Dict) -> str:
        """Analyze semantic intent from name and parameters"""
        combined = f"{name} {json.dumps(params)}"
        
        for pattern, intent in SEMANTIC_PATTERNS.items():
            if re.search(pattern, combined, re.IGNORECASE):
                return intent
        
        return "unknown"
    
    def _extract_config(self, params: Dict, capability: str) -> Dict:
        """Extract relevant config from parameters"""
        config = {}
        
        # Common parameter mappings
        param_mappings = {
            "prompt": ["prompt", "text", "message", "content", "query"],
            "image": ["image", "imageUrl", "image_url", "file", "attachment"],
            "model": ["model", "modelId", "model_id"],
        }
        
        for our_key, their_keys in param_mappings.items():
            for their_key in their_keys:
                if their_key in params and params[their_key]:
                    config[our_key] = params[their_key]
                    break
        
        return config
    
    def _extract_schedule(self, workflow_json: Dict) -> Optional[Dict]:
        """Extract schedule information if present"""
        nodes = workflow_json.get("nodes", [])
        for node in nodes:
            if node.get("type") == "n8n-nodes-base.schedule":
                params = node.get("parameters", {})
                return {
                    "type": "cron",
                    "cron": params.get("rule", {}).get("cronExpression", ""),
                }
        return None
    
    def _calculate_complexity(self, node_count: int, analysis: WorkflowAnalysis) -> float:
        """Calculate workflow complexity score (0-1)"""
        score = min(node_count / 50, 1.0) * 0.3
        
        if analysis.has_conditional_logic:
            score += 0.2
        if analysis.has_loops:
            score += 0.2
        if analysis.has_ai_generation:
            score += 0.1
        if analysis.has_api_calls:
            score += 0.1
        if len(analysis.triggers) > 1:
            score += 0.1
        
        return min(score, 1.0)


# Convenience functions
def convert_any_workflow(workflow_json: Any) -> Tuple[Dict, WorkflowAnalysis]:
    """Convert any workflow format to our unified format"""
    converter = EnhancedUniversalConverter()
    return converter.convert_workflow(workflow_json)


def detect_workflow_platform(workflow_json: Any) -> str:
    """Detect what platform a workflow is from"""
    converter = EnhancedUniversalConverter()
    platform = converter.detect_platform(workflow_json)
    return platform.value


def analyze_workflow(workflow_json: Any) -> WorkflowAnalysis:
    """Analyze a workflow without fully converting it"""
    converter = EnhancedUniversalConverter()
    _, analysis = converter.convert_workflow(workflow_json)
    return analysis
