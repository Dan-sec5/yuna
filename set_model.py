import sys, json, os

def get_installed_models():
    try:
        import ollama
        resp = ollama.list()
        if hasattr(resp, "models"):
            return [m.model for m in resp.models]
        elif isinstance(resp, dict) and "models" in resp:
            return [m.get("model", m.get("name")) for m in resp["models"]]
    except Exception:
        pass
    return []

def main():
    installed = get_installed_models()
    if len(sys.argv) < 2:
        print("ℹ️  Uso: python set_model.py <nombre_del_modelo>")
        print("\nModelos detectados en Ollama:")
        if installed:
            for m in installed:
                print(f"  - {m}")
        else:
            print("  (No se pudo obtener la lista de Ollama)")
        return

    target_model = sys.argv[1]
    cfg_path = "config/config.json"
    cfg = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}

    cfg["model"] = target_model
    cfg.setdefault("models", {})
    cfg["models"]["agent"] = target_model
    cfg["models"]["chat"] = target_model
    cfg["models"]["fast"] = target_model

    cfg.setdefault("ollama", {})
    cfg["ollama"]["host"] = cfg["ollama"].get("host", "http://localhost:11434")

    os.makedirs("config", exist_ok=True)
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

    print(f"✅ Modelo cambiado exitosamente a: '{target_model}'")

if __name__ == "__main__":
    main()
