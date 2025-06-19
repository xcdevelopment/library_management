#!/usr/bin/env python3
"""
図書館システム自動リマインダー実行スクリプト

使用方法:
docker-compose exec web python run_scheduler.py

または、直接実行:
docker-compose exec -e PYTHONPATH=/app web python run_scheduler.py
"""

import os
import sys

# PYTHONPATHを設定
sys.path.insert(0, '/app')
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# スケジューラーを実行
if __name__ == '__main__':
    from scheduler import main
    main()