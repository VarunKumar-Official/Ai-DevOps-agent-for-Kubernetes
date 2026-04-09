from flask import Flask, request, jsonify, render_template_string
from agent import DevOpsAgent

app = Flask(__name__)
agent = DevOpsAgent()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>DevOps AI Agent</title>
    <style>
        body { font-family: Arial; max-width: 900px; margin: 50px auto; padding: 20px; }
        h1 { color: #333; }
        #chat { border: 1px solid #ddd; height: 400px; overflow-y: scroll; padding: 15px; margin: 20px 0; background: #f9f9f9; }
        .message { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .user { background: #e3f2fd; text-align: right; }
        .agent { background: #f1f8e9; }
        input { width: 80%; padding: 10px; font-size: 16px; }
        button { padding: 10px 20px; font-size: 16px; background: #4CAF50; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🤖 DevOps AI Agent</h1>
    <div id="chat"></div>
    <div>
        <input type="text" id="query" placeholder="Ask me anything about DevOps..." onkeypress="if(event.key==='Enter') sendQuery()">
        <button onclick="sendQuery()">Send</button>
    </div>
    <script>
        function sendQuery() {
            const query = document.getElementById('query').value;
            if (!query) return;
            addMessage('user', query);
            document.getElementById('query').value = '';
            fetch('/query', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({query}) })
            .then(r => r.json()).then(data => addMessage('agent', data.response));
        }
        function addMessage(type, text) {
            const chat = document.getElementById('chat');
            const msg = document.createElement('div');
            msg.className = 'message ' + type;
            msg.innerHTML = '<strong>' + (type === 'user' ? 'You' : 'Agent') + ':</strong><br>' + text.replace(/\\n/g, '<br>');
            chat.appendChild(msg);
            chat.scrollTop = chat.scrollHeight;
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/query', methods=['POST'])
def query():
    user_query = request.json.get('query', '')
    if not user_query:
        return jsonify({'error': 'No query provided'}), 400
    return jsonify({'query': user_query, 'response': agent.process_query(user_query)})

if __name__ == '__main__':
    print("Initializing DevOps AI Agent...")
    agent.initialize_rag()
    print("Starting web server on http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
