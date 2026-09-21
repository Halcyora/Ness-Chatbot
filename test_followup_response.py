#!/usr/bin/env python
"""Test actual responses from follow-up questions with context."""

import requests

# Clear cache
requests.post('http://localhost:8080/session/clear-cache')

session_id = 'demo-followup'

# Step 1: Get news
print("1. Getting latest news...")
r1 = requests.post('http://localhost:8080/message', json={
    'site_id': 'kkr',
    'message': 'Show latest news',
    'session_id': session_id
})
reply1 = r1.json()['reply']
print(reply1[:300] + "...\n")

# Step 2: Ask about first news
print("2. Asking about the first one...")
r2 = requests.post('http://localhost:8080/message', json={
    'site_id': 'kkr',
    'message': 'tell me more about the first one',
    'session_id': session_id
})
print("Handler:", r2.json()['trace']['handler'])
print("Response:", r2.json()['reply'][:300] + "...\n")

# Step 3: Different follow-up
print("3. Asking specifically about Flash Macro...")
r3 = requests.post('http://localhost:8080/message', json={
    'site_id': 'kkr',
    'message': 'which one is the flash macro article',
    'session_id': session_id
})
print("Handler:", r3.json()['trace']['handler'])
print("Response:", r3.json()['reply'][:300] + "...")
