# Roadmap

## Executar em modo local/LAN

No PowerShell, a partir da raiz do projeto:

```powershell
.\scripts\start_income_lan.ps1
```

O script executa o equivalente a:

```powershell
python -B -m uvicorn income_analytics.main:app --host 0.0.0.0 --port 8000
```

Com o computador no endereço `192.168.1.82`, a interface fica disponível em
`http://127.0.0.1:8000` no próprio computador e em `http://192.168.1.82:8000`
para dispositivos na mesma rede local. O acesso externo pelo roteador não faz
parte dessa configuração e não deve receber port forwarding.

## v0.1.0
- Project bootstrap
- FastAPI
- CI
- Initial architecture

## v0.2.0
- Core Domain
- Master Data
- Unit tests
- Static typing
- Code quality

## v0.3.0 (Next)
- Financial Event
- Portfolio
- Account
- Event Engine foundation
