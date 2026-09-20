REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PS3 Firmware Test Report</title>
    <style>
        :root {
            --bg-color: #1a1a2e;
            --card-bg: #16213e;
            --accent-color: #0f3460;
            --highlight: #e94560;
            --text-main: #ffffff;
            --text-muted: #b0b0b0;
            --pass-color: #4caf50;
            --fail-color: #f44336;
            --skip-color: #ff9800;
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            padding: 20px 0;
            border-bottom: 2px solid var(--accent-color);
            margin-bottom: 30px;
        }
        h1 { margin: 0; color: var(--highlight); }
        h2 { border-bottom: 1px solid var(--accent-color); padding-bottom: 10px; }
        
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background-color: var(--card-bg);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .stat-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .progress-bar-container {
            background-color: #333;
            border-radius: 4px;
            height: 20px;
            margin-top: 10px;
            overflow: hidden;
        }
        .progress-bar {
            height: 100%;
            background-color: var(--highlight);
        }
        
        .test-list {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }
        .test-card {
            background-color: var(--card-bg);
            border-left: 5px solid gray;
            border-radius: 4px;
            padding: 15px;
        }
        .test-card.passed { border-color: var(--pass-color); }
        .test-card.failed { border-color: var(--fail-color); }
        .test-card.skipped { border-color: var(--skip-color); }
        
        .test-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
        }
        .test-title { font-size: 1.2em; font-weight: bold; }
        .status-badge {
            padding: 5px 10px;
            border-radius: 4px;
            font-weight: bold;
            text-transform: uppercase;
        }
        .status-passed { background-color: var(--pass-color); color: white; }
        .status-failed { background-color: var(--fail-color); color: white; }
        .status-skipped { background-color: var(--skip-color); color: white; }
        
        .test-details {
            display: none;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid var(--accent-color);
        }
        
        .evidence-box {
            background-color: #0d1117;
            padding: 10px;
            border-radius: 4px;
            font-family: monospace;
            white-space: pre-wrap;
            overflow-x: auto;
            color: var(--text-muted);
        }
        .failure-diagnosis {
            color: var(--highlight);
            font-weight: bold;
            margin-top: 10px;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid var(--accent-color);
        }
        th { background-color: var(--accent-color); }
        
        .metadata-section {
            margin-top: 40px;
            padding: 20px;
            background-color: var(--card-bg);
            border-radius: 8px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>PS3 Autonomous Firmware Testing</h1>
            <p>Execution Report</p>
        </header>

        <div class="dashboard">
            <div class="stat-card">
                <div>Total Tests</div>
                <div class="stat-value">{{ summary.total }}</div>
            </div>
            <div class="stat-card" style="border-bottom: 4px solid var(--pass-color)">
                <div>Passed</div>
                <div class="stat-value" style="color: var(--pass-color)">{{ summary.passed }}</div>
            </div>
            <div class="stat-card" style="border-bottom: 4px solid var(--fail-color)">
                <div>Failed</div>
                <div class="stat-value" style="color: var(--fail-color)">{{ summary.failed }}</div>
            </div>
            <div class="stat-card" style="border-bottom: 4px solid var(--skip-color)">
                <div>Skipped</div>
                <div class="stat-value" style="color: var(--skip-color)">{{ summary.skipped }}</div>
            </div>
            <div class="stat-card">
                <div>Coverage</div>
                <div class="stat-value">{{ summary.coverage_pct }}%</div>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: {{ summary.coverage_pct }}%"></div>
                </div>
            </div>
            <div class="stat-card">
                <div>Execution Time</div>
                <div class="stat-value">{{ summary.execution_time }}s</div>
            </div>
        </div>

        <h2>Test Execution Results</h2>
        <div class="test-list">
            {% for test in tests %}
            <div class="test-card {{ test.status|lower }}">
                <div class="test-header" onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'block' ? 'none' : 'block'">
                    <div class="test-title">{{ test.name }}</div>
                    <div class="status-badge status-{{ test.status|lower }}">{{ test.status }}</div>
                </div>
                <div class="test-details">
                    <p><strong>Description:</strong> {{ test.description }}</p>
                    <p><strong>Duration:</strong> {{ test.duration }}s</p>
                    
                    {% if test.status|lower == 'failed' %}
                    <div class="failure-diagnosis">
                        Diagnosis: {{ test.diagnosis }}
                    </div>
                    {% endif %}
                    
                    <h4>Execution Evidence</h4>
                    <div class="evidence-box">{{ test.evidence }}</div>
                    
                    {% if test.uart_output %}
                    <h4>UART Output</h4>
                    <div class="evidence-box">{{ test.uart_output }}</div>
                    {% endif %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        {% if failures %}
        <h2>Failure Analysis</h2>
        <table>
            <thead>
                <tr>
                    <th>Test Name</th>
                    <th>Diagnosis</th>
                    <th>Source Code Location</th>
                </tr>
            </thead>
            <tbody>
                {% for failure in failures %}
                <tr>
                    <td>{{ failure.name }}</td>
                    <td style="color: var(--highlight);">{{ failure.diagnosis }}</td>
                    <td><a href="{{ failure.source_link }}" style="color: var(--text-main);">{{ failure.source_location }}</a></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}

        <div class="metadata-section">
            <h2>Run Metadata</h2>
            <p><strong>Timestamp:</strong> {{ metadata.timestamp }}</p>
            <p><strong>Firmware Target:</strong> {{ metadata.firmware }}</p>
            <p><strong>Simulator:</strong> {{ metadata.simulator }}</p>
            <p><strong>Agent Version:</strong> {{ metadata.version }}</p>
            
            <div class="content-section" style="margin-top: 30px;">
                <h3>Telemetry Viewer</h3>
                {% if rig_view_content %}
                <iframe srcdoc="{{ rig_view_content | e }}" style="width:100%; height:700px; border:1px solid var(--accent-color); border-radius:4px;"></iframe>
                {% else %}
                <p style="color: var(--text-muted);">No telemetry data available for this run.</p>
                {% endif %}
            </div>

            {% if agent_activity %}
            <h3>Agent Activity Log</h3>
            <ul>
                {% for activity in agent_activity %}
                <li>{{ activity }}</li>
                {% endfor %}
            </ul>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""
