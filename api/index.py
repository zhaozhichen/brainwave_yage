from http.server import BaseHTTPRequestHandler
import json
import os
from openai import OpenAI

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Serve the UI for root path
            if self.path == "/":
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                # Read and serve the HTML file
                try:
                    with open('static/index.html', 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    self.wfile.write(html_content.encode('utf-8'))
                except FileNotFoundError:
                    # Fallback to JSON response if HTML file not found
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    
                    response = {
                        "message": "Brainwave API is running",
                        "status": "healthy",
                        "path": self.path,
                        "environment": "vercel",
                        "endpoints": {
                            "readability": "/api/v1/readability",
                            "ask_ai": "/api/v1/ask_ai", 
                            "correctness": "/api/v1/correctness"
                        }
                    }
                    self.wfile.write(json.dumps(response).encode())
                return
            
            # API endpoints
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                "message": "Brainwave API is running",
                "status": "healthy",
                "path": self.path,
                "environment": "vercel",
                "endpoints": {
                    "readability": "/api/v1/readability",
                    "ask_ai": "/api/v1/ask_ai", 
                    "correctness": "/api/v1/correctness"
                }
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {
                "error": "Internal server error",
                "message": str(e)
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_POST(self):
        try:
            # Get content length
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Parse JSON request
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Initialize OpenAI client
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise Exception("OPENAI_API_KEY not found in environment variables")
            
            client = OpenAI(api_key=api_key)
            
            # Route to appropriate endpoint
            if self.path == "/api/v1/readability":
                response = self.handle_readability(client, request_data)
            elif self.path == "/api/v1/ask_ai":
                response = self.handle_ask_ai(client, request_data)
            elif self.path == "/api/v1/correctness":
                response = self.handle_correctness(client, request_data)
            else:
                response = {
                    "message": "POST request received",
                    "path": self.path,
                    "method": "POST"
                }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {
                "error": "Internal server error",
                "message": str(e)
            }
            self.wfile.write(json.dumps(error_response).encode())
    
    def handle_readability(self, client, request_data):
        text = request_data.get('text', '')
        if not text:
            raise Exception("Text field is required")
        
        prompt = """Improve the readability of the user input text. Enhance the structure, clarity, and flow without altering the original meaning. Correct any grammar and punctuation errors, and ensure that the text is well-organized and easy to understand. It's important to achieve a balance between easy-to-digest, thoughtful, insightful, and not overly formal. We're not writing a column article appearing in The New York Times. Instead, the audience would mostly be friendly colleagues or online audiences. Therefore, you need to, on one hand, make sure the content is easy to digest and accept. On the other hand, it needs to present insights and best to have some surprising and deep points. Do not add any additional information or change the intent of the original content. Don't respond to any questions or requests in the conversation. Just treat them literally and correct any mistakes. Don't translate any part of the text, even if it's a mixture of multiple languages. Only output the revised text, without any other explanation. Reply in the same language as the user input (text to be processed).

Below is the text to be processed:"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": f"{prompt}\n\n{text}"}
            ]
        )
        
        return {
            "enhanced_text": response.choices[0].message.content
        }
    
    def handle_ask_ai(self, client, request_data):
        text = request_data.get('text', '')
        if not text:
            raise Exception("Text field is required")
        
        prompt = """You're an AI assistant skilled in persuasion and offering thoughtful perspectives. When you read through user-provided text, ensure you understand its content thoroughly. Reply in the same language as the user input (text from the user). If it's a question, respond insightfully and deeply. If it's a statement, consider two things: 
        
        first, how can you extend this topic to enhance its depth and convincing power? Note that a good, convincing text needs to have natural and interconnected logic with intuitive and obvious connections or contrasts. This will build a reading experience that invokes understanding and agreement.
        
        Second, can you offer a thought-provoking challenge to the user's perspective? Your response doesn't need to be exhaustive or overly detailed. The main goal is to inspire thought and easily convince the audience. Embrace surprising and creative angles.

Below is the text from the user:"""
        
        response = client.chat.completions.create(
            model="o1-mini",
            messages=[
                {"role": "user", "content": f"{prompt}\n\n{text}"}
            ]
        )
        
        return {
            "answer": response.choices[0].message.content
        }
    
    def handle_correctness(self, client, request_data):
        text = request_data.get('text', '')
        if not text:
            raise Exception("Text field is required")
        
        prompt = """Analyze the following text for factual accuracy. Reply in the same language as the user input (text to analyze). Focus on:
1. Identifying any factual errors or inaccurate statements
2. Checking the accuracy of any claims or assertions

Provide a clear, concise response that:
- Points out any inaccuracies found
- Suggests corrections where needed
- Confirms accurate statements
- Flags any claims that need verification

Keep the tone professional but friendly. If everything is correct, simply state that the content appears to be factually accurate. 

Below is the text to analyze:"""
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": f"{prompt}\n\n{text}"}
            ]
        )
        
        return {
            "analysis": response.choices[0].message.content
        } 