from blackboard_store import BlackboardStore

def main():
    store = BlackboardStore(data_path="blackboard_instance.json", schema_path="blackboard_schema.json")
    data = store.read()
    print("Initial version:", data["version"])

    store.update_current_question("请设计一个短链接系统", "System Design", "Chinese", "manual_input", 0.9)
    store.update_agent_state("Perception", "done", "Detected System Design question.", {"selected_agent": "Tech/Code"})
    store.append_history("请设计一个短链接系统", "从需求、API、数据库表、短码生成、缓存和高并发几个方面回答。", "Tech/Code", "System Design", {"clarity":0.8,"correctness":0.8,"resume_alignment":0.5,"human_like":0.7})

    updated = store.read()
    print("Updated version:", updated["version"])
    print("Current question:", updated["current_question"]["text"])
    print("History count:", len(updated["history"]))

if __name__ == "__main__":
    main()
