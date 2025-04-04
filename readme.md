🧰 Open WebUI Tools
A growing collection of custom tools built for use with Open WebUI that enable large language models (LLMs) to interact with external APIs in a controlled, observable, and context-aware way.

This repo includes integrations with APIs like Home Assistant, allowing models like Gemini or GPT to intelligently query, control, and reason across complex systems — all while emitting detailed markdown responses to support LLM decision-making.

🏠 Home Assistant Tool
This module exposes Home Assistant’s REST API in a structured and LLM-friendly format. It’s designed to give agents everything they need to discover entities, inspect their attributes, reason over available actions, and issue control commands with confidence.

✨ Features
🔍 Entity Discovery
Retrieve entities by domain (e.g. light, fan, switch) or fetch all entities grouped by domain.

🧠 Context-Aware Observability
Emits markdown tables and summaries of device states, attributes, and actions for LLMs to interpret.

🛠️ Control & Configuration
Trigger services like turn_on, turn_off, toggle, or pass custom data (e.g., brightness, temperature) via payloads.

🔒 Token-Based Authentication
Uses a long-lived access token and Home Assistant’s REST API for secure local communication.

📦 Methods

 - getEntitiesByDomain(domain)	Lists all devices in a domain like light, fan, etc.
 - getAllEntities()	Returns all devices grouped by domain, ideal for ambiguous commands.
 - getAttributesForEntity(entity_id)	Retrieves the current state and all attributes of a specific entity.
 - controlEntity(entity_id, domain, service)	Performs actions like turning devices on or off.
 - setEntityAttribute(entity_id, domain, service, data)	Sends service calls with custom data (e.g., brightness, color, temperature).
 - getAvailableServicesForDomain(domain)	Lists available services (e.g., turn_on, toggle) for a given domain.
 
⚙️ Configuration
Before use, set your Home Assistant URL and token:

 - tools = Tools()
 - tools.valves.ha_url = "http://homeassistant.local:8123"
 - tools.valves.ha_api_key = "<YOUR_LONG_LIVED_ACCESS_TOKEN>"

🔑 Note: You must create a long-lived access token in Home Assistant to use this tool.

🧪 Observability
Each method optionally accepts __event_emitter__, which should be a coroutine capable of receiving dict events like:

{
  "type": "status",
  "data": { "description": "Doing something...", "done": false }
}
This makes the tool ideal for use with Open WebUI’s function-calling system, as it emits markdown messages and progress updates that help the LLM make better decisions.

🧠 Philosophy
These tools are designed with LLM-first reasoning in mind:

Emit structured markdown and summaries

Provide full context without assuming control

Let the model reason before acting

You can think of this repo as the middleware between external APIs and intelligent agents.

📄 License
MIT License

Let me know if you'd like to include examples of usage with Open WebUI or a full example function schema.