import schedule
import time
from datetime import datetime
from agent import DevOpsAgent

class TaskScheduler:
    def __init__(self):
        self.agent = DevOpsAgent()
        self.agent.initialize_rag()

    def daily_health_check(self):
        print(f"\n[{datetime.now()}] Running daily health check...")
        for task in ["Check all pods status", "Show nodes resource usage", "List recent error events", "Check high restart counts"]:
            print(f"\n→ {task}")
            print(self.agent.process_query(task))

    def hourly_monitor(self):
        print(f"\n[{datetime.now()}] Hourly monitoring...")
        print(self.agent.process_query("Check for any failing pods"))

    def start(self):
        schedule.every().day.at("09:00").do(self.daily_health_check)
        schedule.every().hour.do(self.hourly_monitor)
        print("Scheduler started:\n- Daily health check: 09:00\n- Hourly monitoring\nPress Ctrl+C to stop\n")
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            print("\nScheduler stopped")

if __name__ == "__main__":
    TaskScheduler().start()
