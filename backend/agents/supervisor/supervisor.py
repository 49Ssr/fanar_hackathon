import json
from openai import OpenAI
from datetime import datetime
from .schema import Context, Payload, SuperVisorResponse 
from .prompt import build_system_prompt, build_self_healing_prompt

class SuperVisorAgent():
    def __init__(self,model_name:str,base_url:str,api_key:str):
        self.model_name= model_name

        self.client=OpenAI(base_url=base_url,api_key=api_key)

    def _get_context(self) -> dict:
        now=datetime.now()

        return {
            "reference_date": now.strftime("%Y-%m-%d"),
            "reference_day": now.strftime("%A").upper(),
            "reference_time": now.strftime("%H:%M:%S")

        }
    
    def _parse_response(self,content: str,query: str,context: dict):
        route = json.loads(content)

        route.setdefault("payload", {})

        route["payload"]["query"] = query
        route["payload"]["context"] = context

        return SuperVisorResponse.model_validate(route)
    
    def _call_model(self,messages):
        response=self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0
        )
        return response
    

    def run(self, query: str) -> dict:

        MAX_RETRIES = 3

        context = self._get_context()

        system_prompt = build_system_prompt(
            context["reference_date"],
            context["reference_day"],
            context["reference_time"]
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        last_error = None

        for attempt in range(1, MAX_RETRIES + 1):

            try:

                response = self._call_model(messages)

                content = response.choices[0].message.content

                validated_route = self._parse_response(
                    content, query, context
                )

                return validated_route

            except Exception as e:

                last_error = str(e)

                print(
                    f"[Supervisor] Attempt {attempt} failed: {last_error}"
                )

                # Self-healing
                if attempt < MAX_RETRIES:

                    messages.append(
                        {
                            "role": "assistant",
                            "content": content if "content" in locals() else ""
                        }
                    )

                    messages.append(
                        {
                            "role": "user",
                            "content":   build_self_healing_prompt(last_error)                      
                        })

        raise ValueError(
            f"Supervisor failed after {MAX_RETRIES} attempts. Last error: {last_error}"
        )
        

