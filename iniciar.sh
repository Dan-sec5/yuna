#!/bin/bash
MEMORIA=$(cat ~/yuna/memoria.txt)
ollama run qwen3:4b "Contexto sobre el usuario: $MEMORIA. Ahora responde como asistente femenino personal."
