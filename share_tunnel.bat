@echo off
title Cloudflare Tunnel - Recording Converter
echo ========================================================
echo   Starting Cloudflare Tunnel for Recording Converter
echo   Local Address: http://localhost:5173
echo ========================================================
echo.
echo Please ensure Vite (npm run dev) and FastAPI are running.
echo.
npx -y cloudflared tunnel --url http://localhost:5173
pause
