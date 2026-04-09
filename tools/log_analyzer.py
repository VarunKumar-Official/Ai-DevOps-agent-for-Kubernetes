import re
from typing import Dict, List

ERROR_PATTERNS = {
    'CrashLoopBackOff': {
        'pattern': r'CrashLoopBackOff',
        'description': 'Pod is crashing repeatedly',
        'suggestions': [
            'Check application logs for errors',
            'Verify container image is correct',
            'Check resource limits (CPU/Memory)',
            'Verify environment variables and config'
        ]
    },
    'OOMKilled': {
        'pattern': r'OOMKilled',
        'description': 'Container killed due to out of memory',
        'suggestions': [
            'Increase memory limits in deployment',
            'Check for memory leaks in application',
            'Review memory usage patterns'
        ]
    },
    '5xx_errors': {
        'pattern': r'(5\d{2}|upstream.*error|502|503|504)',
        'description': 'Server errors detected',
        'suggestions': [
            'Check upstream service health',
            'Verify service endpoints',
            'Check for resource exhaustion',
            'Review ingress configuration'
        ]
    },
    'timeout': {
        'pattern': r'(timeout|timed out|deadline exceeded)',
        'description': 'Timeout errors detected',
        'suggestions': [
            'Increase timeout values',
            'Check network connectivity',
            'Verify service response time',
            'Check for slow database queries'
        ]
    }
}

def analyze_logs(log_text: str) -> Dict:
    """Analyze logs and detect common issues"""
    detected_issues = []

    for issue_name, config in ERROR_PATTERNS.items():
        if re.search(config['pattern'], log_text, re.IGNORECASE):
            detected_issues.append({
                'issue': issue_name,
                'description': config['description'],
                'suggestions': config['suggestions']
            })

    return {
        'issues_found': len(detected_issues),
        'detected_issues': detected_issues,
        'log_summary': log_text[:500] if log_text else "No logs provided"
    }

def get_analysis_prompt(log_text: str) -> str:
    """Generate prompt for LLM analysis"""
    analysis = analyze_logs(log_text)

    prompt = f"""Analyze these logs and provide root cause analysis:

Logs:
{log_text[:1000]}

Detected Issues: {analysis['issues_found']}
"""

    for issue in analysis['detected_issues']:
        prompt += f"\n- {issue['description']}"

    prompt += "\n\nProvide: 1) Root cause 2) Recommended fix"

    return prompt
