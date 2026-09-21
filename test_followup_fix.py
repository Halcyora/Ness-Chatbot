#!/usr/bin/env python
"""Test that follow-up questions route to RAG instead of re-calling tools."""

import requests

# Clear cache
requests.post('http://localhost:8080/session/clear-cache')

session_id = 'test-followup-fix'
print('=== Testing Follow-up Question Routing ===\n')

# Message 1: Show latest news
response1 = requests.post('http://localhost:8080/message', json={
    'site_id': 'kkr',
    'message': 'Show latest news',
    'session_id': session_id
})
print('1. Show latest news')
print('   Handler:', response1.json().get('handler', 'N/A'))
print('   Route:', response1.json()['trace'].get('handler', 'N/A'))
print('   Result: News list' if 'Found' in response1.json()['reply'] else '   Result: Other')
print()

# Message 2: Follow-up asking about the first news
response2 = requests.post('http://localhost:8080/message', json={
    'site_id': 'kkr',
    'message': 'tell me more about the first news',
    'session_id': session_id
})
print('2. tell me more about the first news')
print('   Handler:', response2.json().get('handler', 'N/A'))
print('   Route:', response2.json()['trace'].get('handler', 'N/A'))
print('   Expected: RAG (not tool - should use conversation history)')
if response2.json()['trace'].get('handler') == 'rag':
    print('   Status: ✓ FIXED!')
else:
    print('   Status: ✗ Still routing to tool')
print()

# Message 3: Follow-up filtering to only Flash Macro
response3 = requests.post('http://localhost:8080/message', json={
    'site_id': 'kkr',
    'message': 'more about only the flash macro news',
    'session_id': session_id
})
print('3. more about only the flash macro news')
print('   Handler:', response3.json().get('handler', 'N/A'))
print('   Route:', response3.json()['trace'].get('handler', 'N/A'))
print('   Expected: RAG (not tool)')
if response3.json()['trace'].get('handler') == 'rag':
    print('   Status: ✓ FIXED!')
else:
    print('   Status: ✗ Still routing to tool')
