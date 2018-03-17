#!/usr/bin/env python

import os
import json

def load_config():
    SHUTTLE_CONFIG = os.environ.get("SHUTTLE_CONFIG", 
        "config/shuttle.json")
    with open(SHUTTLE_CONFIG) as fp:
        config = json.loads(fp.read())
    
    return config

config = load_config()