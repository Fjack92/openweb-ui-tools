"""
title: Home Assistant Controls
author: Fred Jack
funding_url: https://github.com/open-webui
version: 0.3
"""

import os
import requests
import json
from datetime import datetime
from pydantic import BaseModel, Field


class Tools:
    def __init__(self):
        self.valves = self.Valves()
        self.entity_cache = {}  # 🔁 Stores last-fetched entities by domain
        self.citation = False

    class Valves(BaseModel):
        ha_url: str = Field(
            "",
            description="Base URL of your Home Assistant instance (e.g., http://homeassistant.local:8123)",
        )
        ha_api_key: str = Field(
            "", description="Home Assistant Long-Lived Access Token"
        )

    async def getEntitiesByDomain(
        self, domain: str, __event_emitter__=None
    ) -> list[dict]:
        """
        Retrieves all Home Assistant entities that belong to a specific domain (e.g., light, switch, fan).

        🧠 Use this to help the model decide which device the user is referring to. For example, when the user says
        'turn off the bedroom light', call this with `domain="light"` and then use the friendly names to match.

        🧠 You do NOT need to match the entity yourself — just surface the full list of friendly names + entity IDs so
        the model can reason across them.

        Emits a markdown-formatted table of devices in the domain.

        :param domain: The domain of devices to retrieve, such as "light", "switch", "fan", etc.
        :return: A list of dicts with entity_id, friendly_name, and domain.
        """
        try:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Querying entities in domain '{domain}'",
                        "done": False,
                    },
                }
            )

            endpoint = f"{self.valves.ha_url}/api/states"
            headers = {
                "Authorization": f"Bearer {self.valves.ha_api_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(endpoint, headers=headers)
            if response.status_code != 200:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Error: {response.status_code}",
                            "done": True,
                        },
                    }
                )
                return [f"Error {response.status_code}: {response.text}"]

            all_states = response.json()
            entities = [
                {
                    "entity_id": entity["entity_id"],
                    "friendly_name": entity["attributes"].get(
                        "friendly_name", "unknown"
                    ),
                    "domain": entity["entity_id"].split(".")[0],
                }
                for entity in all_states
                if entity["entity_id"].startswith(f"{domain}.")
            ]

            # Cache result
            self.entity_cache[domain] = entities

            # Emit markdown for Gemini to reason over
            markdown_table = "**Discovered entities in domain** `" + domain + "`:\n\n"
            markdown_table += (
                "| Entity ID | Friendly Name |\n|-----------|----------------|\n"
            )
            for e in entities:
                markdown_table += f"| `{e['entity_id']}` | {e['friendly_name']} |\n"

            await __event_emitter__(
                {
                    "type": "message",
                    "data": {"content": markdown_table},
                }
            )

            await __event_emitter__(
                {
                    "type": "message",
                    "data": {
                        "content": (
                            "🧠 If you want to know the *current state* of one of these devices, "
                            "call `getAttributesForEntity(entity_id)` with the correct `entity_id`."
                        ),
                    },
                }
            )

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Discovery complete", "done": True},
                }
            )

            return entities

        except Exception as e:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Exception occurred: {e}", "done": True},
                }
            )
            return [f"An error occurred: {e}"]

    async def getAllEntities(self, __event_emitter__=None) -> dict:
        """
        Retrieves all entities from Home Assistant, grouped by domain.

        🧠 Use this if the user gives a broad or ambiguous command like "turn on the hallway device",
        and you want to see *everything* available across all domains.

        You can then reason over the grouped list and decide what domain/service to use.

        Emits markdown tables for each domain.

        :return: A dict of domain -> list of entities
        """
        try:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Querying all entities", "done": False},
                }
            )

            endpoint = f"{self.valves.ha_url}/api/states"
            headers = {
                "Authorization": f"Bearer {self.valves.ha_api_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(endpoint, headers=headers)
            if response.status_code != 200:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Error: {response.status_code}",
                            "done": True,
                        },
                    }
                )
                return {}

            all_states = response.json()

            grouped = {}
            for entity in all_states:
                domain = entity["entity_id"].split(".")[0]
                obj = {
                    "entity_id": entity["entity_id"],
                    "friendly_name": entity["attributes"].get(
                        "friendly_name", "unknown"
                    ),
                    "domain": domain,
                }
                grouped.setdefault(domain, []).append(obj)

            self.entity_cache = grouped

            # Emit markdown tables for each domain
            for domain, items in grouped.items():
                markdown_table = f"### Domain: `{domain}`\n\n"
                markdown_table += (
                    "| Entity ID | Friendly Name |\n|-----------|----------------|\n"
                )
                for e in items:
                    markdown_table += f"| `{e['entity_id']}` | {e['friendly_name']} |\n"

                await __event_emitter__(
                    {
                        "type": "message",
                        "data": {"content": markdown_table},
                    }
                )

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Full discovery complete", "done": True},
                }
            )

            return grouped

        except Exception as e:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Exception occurred: {e}", "done": True},
                }
            )
            return {}

    async def controlEntity(
        self, entityID: str, domain: str, service: str, __event_emitter__=None
    ) -> str:
        """
        Sends a command to control a Home Assistant entity, such as turning on or off a device.

        🧠 Only call this when you already know the full `entity_id`, the correct `domain`, and the intended `service`.
        Gemini should reason this from prior entity discovery.

        Example usage:
          → domain = "light"
          → entityID = "light.office_fan"
          → service = "turn_on"

        :param entityID: The full entity_id to target (e.g., "light.office_fan").
        :param domain: The domain of the device (e.g., "light", "switch").
        :param service: The action to perform (e.g., "turn_on", "turn_off").
        :return: A JSON object summarizing the result.
        """
        try:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Sending {service} command to {entityID}",
                        "done": False,
                    },
                }
            )

            endpoint = f"{self.valves.ha_url}/api/services/{domain}/{service}"
            payload = json.dumps({"entity_id": entityID})
            headers = {
                "Authorization": f"Bearer {self.valves.ha_api_key}",
                "Content-Type": "application/json",
            }

            await __event_emitter__(
                {
                    "type": "message",
                    "data": {
                        "content": f"**Request Details**\n- Endpoint: `{endpoint}`\n- Payload: ```json\n{payload}\n```"
                    },
                }
            )

            response = requests.post(endpoint, data=payload, headers=headers)

            await __event_emitter__(
                {
                    "type": "message",
                    "data": {
                        "content": f"**Response Details**\n- Status: `{response.status_code}`\n- Body: ```json\n{response.text}\n```"
                    },
                }
            )

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Command complete", "done": True},
                }
            )

            return json.dumps(
                {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "entity": entityID,
                    "service": service,
                    "request_url": endpoint,
                    "request_payload": json.loads(payload),
                    "response": response.text,
                }
            )

        except Exception as e:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Error occurred: {e}", "done": True},
                }
            )
            return json.dumps({"success": False, "error": str(e)})

    async def getAvailableServicesForDomain(
        self, domain: str, __event_emitter__=None
    ) -> list[str]:
        """
        Retrieves all available services for a given Home Assistant domain.

        🧠 Use this if you're unsure which actions are allowed for a domain (like 'light', 'fan', 'switch', etc).
        The model can use this to decide whether to call `turn_on`, `turn_off`, `toggle`, etc.

        Emits a markdown list of available services for the domain.

        :param domain: The domain of the devices (e.g. 'light', 'fan', 'switch', etc.)
        :return: A list of available service names (e.g., ['turn_on', 'turn_off'])
        """
        try:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Fetching available services for domain '{domain}'",
                        "done": False,
                    },
                }
            )

            endpoint = f"{self.valves.ha_url}/api/services"
            headers = {
                "Authorization": f"Bearer {self.valves.ha_api_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(endpoint, headers=headers)
            if response.status_code != 200:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Error: {response.status_code}",
                            "done": True,
                        },
                    }
                )
                return []

            all_services = response.json()
            """
            await __event_emitter__(
                {
                    "type": "message",
                    "data": {
                        "content": f"**Raw API Response:** ```json\n{json.dumps(all_services, indent=2)}\n```"
                    },
                }
            )
            """
            # Find the matching domain entry
            matching = next((s for s in all_services if s["domain"] == domain), None)
            if not matching:
                await __event_emitter__(
                    {
                        "type": "message",
                        "data": {"content": f"No services found for domain `{domain}`"},
                    }
                )
                return []

            services = matching["services"]

            markdown = f"**Available services for domain** `{domain}`:\n\n"
            for s in services:
                markdown += f"- `{s}`\n"

            await __event_emitter__(
                {
                    "type": "message",
                    "data": {"content": markdown},
                }
            )

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Service list complete", "done": True},
                }
            )

            return services

        except Exception as e:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Error occurred: {e}", "done": True},
                }
            )
            return []

    async def getAttributesForEntity(
        self, entity_id: str, __event_emitter__=None
    ) -> dict:
        """
        Retrieves the current state and all attributes for a specific Home Assistant entity.

        🧠 Use this to determine what properties are available (e.g., brightness, color, speed),
        and what the current values are.

        This is helpful before issuing commands like `set_percentage`, `set_speed`, etc.

        Emits a markdown-formatted summary for reasoning.

        :param entity_id: The full entity_id (e.g. 'light.office_fan', 'fan.living_room')
        :return: A dict containing state and attributes
        """
        try:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Querying current state of `{entity_id}`",
                        "done": False,
                    },
                }
            )

            endpoint = f"{self.valves.ha_url}/api/states/{entity_id}"
            headers = {
                "Authorization": f"Bearer {self.valves.ha_api_key}",
                "Content-Type": "application/json",
            }

            response = requests.get(endpoint, headers=headers)
            if response.status_code != 200:
                await __event_emitter__(
                    {
                        "type": "status",
                        "data": {
                            "description": f"Error: {response.status_code}",
                            "done": True,
                        },
                    }
                )
                return {}

            data = response.json()
            state = data.get("state")
            attributes = data.get("attributes", {})

            markdown = f"**Current state for `{entity_id}`**: `{state}`\n\n"
            markdown += "**Attributes:**\n\n"
            for key, value in attributes.items():
                markdown += f"- **{key}**: `{value}`\n"

            await __event_emitter__(
                {
                    "type": "message",
                    "data": {"content": markdown},
                }
            )

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Attribute query complete", "done": True},
                }
            )

            return {"state": state, "attributes": attributes}

        except Exception as e:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Error occurred: {e}", "done": True},
                }
            )
            return {"error": str(e)}

    async def setEntityAttribute(
        self,
        entity_id: str,
        domain: str,
        service: str,
        data: dict,
        __event_emitter__=None,
    ) -> str:
        """
        Sends a service command with a custom data payload to modify an entity in Home Assistant.

        🧠 Use this when you need to control a device AND pass additional parameters.
        This is most useful when setting brightness, percentage, color, temperature, etc.

        Examples:
          - Set brightness on a light
          - Set temperature on a thermostat
          - Set percentage on a fan

        Use this if the action cannot be completed using only entity_id (i.e., `controlEntity` is not enough).

        :param entity_id: Full entity_id (e.g., "light.office_fan")
        :param domain: The domain of the device (e.g., "light", "fan", "climate")
        :param service: The Home Assistant service to call (e.g., "turn_on", "set_temperature")
        :param data: Dictionary of additional parameters (e.g., { "brightness_pct": 40 })
        :return: A JSON summary of the request and response
        """
        try:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "description": f"Sending `{service}` with data to `{entity_id}`",
                        "done": False,
                    },
                }
            )

            endpoint = f"{self.valves.ha_url}/api/services/{domain}/{service}"

            # Build payload by combining entity ID with extra data fields
            payload_dict = {"entity_id": entity_id, **data}
            payload = json.dumps(payload_dict)

            headers = {
                "Authorization": f"Bearer {self.valves.ha_api_key}",
                "Content-Type": "application/json",
            }

            # Emit request data for debugging/observability
            await __event_emitter__(
                {
                    "type": "message",
                    "data": {
                        "content": f"**Request Details**\n- Endpoint: `{endpoint}`\n- Payload: ```json\n{payload}\n```"
                    },
                }
            )

            response = requests.post(endpoint, data=payload, headers=headers)

            # Emit response details
            await __event_emitter__(
                {
                    "type": "message",
                    "data": {
                        "content": f"**Response Details**\n- Status: `{response.status_code}`\n- Body: ```json\n{response.text}\n```"
                    },
                }
            )

            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": "Attribute change complete", "done": True},
                }
            )

            return json.dumps(
                {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "entity": entity_id,
                    "domain": domain,
                    "service": service,
                    "payload": payload_dict,
                    "response": response.text,
                }
            )

        except Exception as e:
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {"description": f"Error occurred: {e}", "done": True},
                }
            )
            return json.dumps({"success": False, "error": str(e)})
