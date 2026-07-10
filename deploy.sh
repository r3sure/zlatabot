#!/usr/bin/env bash
set -e

export DEBIAN_FRONTEND=noninteractive

cd /root

echo "=== 1. Устанавливаем Docker ==="
apt-get update -qq
apt-get install -y -qq ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
systemctl enable --now docker

echo "=== 2. Клонируем бота ==="
if [ -d zlatabot ]; then
  cd zlatabot && git pull
else
  git clone https://github.com/r3sure/zlatabot.git && cd zlatabot
fi

echo "=== 3. Создаём .env ==="
if [ -f .env ]; then
  echo ".env уже существует, пропускаем"
else
  cp .env.example .env
  echo ""
  echo "===== Настройка бота ====="
  read -p "Введите TELEGRAM_BOT_TOKEN (из @BotFather): " token
  sed -i "s/your_token_here/$token/" .env
  echo ""
  echo "Теперь LLM-провайдер (откуда бот берёт ответы):"
  echo "  1) DeepSeek через provod.ai (рекомендуется, рубли)"
  echo "  2) Groq (нужен API-ключ)"
  read -p "Выберите 1 или 2: " llm_choice
  if [ "$llm_choice" = "1" ]; then
    sed -i 's/LLM_PROVIDER=groq/LLM_PROVIDER=deepseek/' .env
    sed -i 's|DEEPSEEK_BASE_URL=.*|DEEPSEEK_BASE_URL=https://api.provod.ai/v1|' .env
    sed -i 's/DEEPSEEK_MODEL=.*/DEEPSEEK_MODEL=deepseek\/deepseek-v4-flash/' .env
    read -p "Введите DEEPSEEK_API_KEY (из provod.ai): " dskey
    sed -i "s|# DEEPSEEK_API_KEY=.*|DEEPSEEK_API_KEY=$dskey|" .env
  else
    read -p "Введите GROQ_API_KEY: " gkey
    sed -i "s/GROQ_API_KEY=.*/GROQ_API_KEY=$gkey/" .env
  fi
  echo ".env создан!"
fi

echo "=== 4. Запускаем бота ==="
docker compose up -d --build

echo ""
echo "===== ГОТОВО ====="
echo "Проверь логи: docker compose logs -f"
echo "Остановить: docker compose stop"
echo "Обновить: git pull && docker compose up -d --build"
