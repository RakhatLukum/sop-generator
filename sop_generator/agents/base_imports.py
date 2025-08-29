# Shared import handling for all agent modules
"""
This module handles the import of autogen components with fallbacks for deployment.
All agent modules should import from this module to ensure consistent behavior.
"""

# Try to import autogen components with fallbacks
try:
    from autogen_agentchat.agents import AssistantAgent
    from autogen_agentchat.messages import TextMessage, BaseChatMessage
    from autogen_agentchat.teams import RoundRobinGroupChat
    AUTOGEN_AVAILABLE = True
except ImportError:
    try:
        from autogen.agentchat.agents import AssistantAgent
        from autogen.agentchat.messages import TextMessage, BaseChatMessage
        from autogen.agentchat.teams import RoundRobinGroupChat
        AUTOGEN_AVAILABLE = True
    except ImportError:
        try:
            from autogen import AssistantAgent
            AUTOGEN_AVAILABLE = True
            
            # Create mock message classes for deployment
            class TextMessage:
                def __init__(self, source, content):
                    self.source = source
                    self.content = content
            
            class BaseChatMessage:
                def __init__(self, source, content):
                    self.source = source
                    self.content = content
            
            class RoundRobinGroupChat:
                def __init__(self, agents):
                    self.agents = agents
                async def run(self, task):
                    return MockResult([])
                    
        except ImportError:
            AUTOGEN_AVAILABLE = False
            
            # Create mock AssistantAgent for deployment
            class AssistantAgent:
                def __init__(self, name, system_message, model_client):
                    self.name = name
                    self.system_message = system_message
                    self.model_client = model_client
                    print(f"Warning: Using mock AssistantAgent for {name}")
                
                async def generate_reply(self, messages):
                    try:
                        # Convert system message to message format
                        full_messages = [
                            {"role": "system", "content": self.system_message}
                        ]
                        
                        # Add user messages
                        if isinstance(messages, str):
                            full_messages.append({"role": "user", "content": messages})
                        elif isinstance(messages, list):
                            full_messages.extend(messages)
                        
                        # Get response from model client
                        response = await self.model_client.create(full_messages)
                        if hasattr(response, 'choices') and len(response.choices) > 0:
                            return response.choices[0].message.content
                        else:
                            return "No response generated"
                    except Exception as e:
                        print(f"Agent {self.name} generate_reply error: {e}")
                        return f"Error generating reply: {e}"
                
                async def run(self, task):
                    try:
                        reply = await self.generate_reply(task)
                        return MockResult([TextMessage(self.name, reply)])
                    except Exception as e:
                        print(f"Agent {self.name} run error: {e}")
                        return MockResult([TextMessage(self.name, f"Error: {e}")])
            
            class TextMessage:
                def __init__(self, source, content):
                    self.source = source
                    self.content = content
            
            class BaseChatMessage:
                def __init__(self, source, content):
                    self.source = source
                    self.content = content
            
            class RoundRobinGroupChat:
                def __init__(self, agents):
                    self.agents = agents
                async def run(self, task):
                    return MockResult([])

class MockResult:
    def __init__(self, messages):
        self.messages = messages

__all__ = ['AssistantAgent', 'TextMessage', 'BaseChatMessage', 'RoundRobinGroupChat', 'MockResult', 'AUTOGEN_AVAILABLE']