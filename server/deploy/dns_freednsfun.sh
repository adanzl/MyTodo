#!/bin/sh
# Certbot manual-auth-hook for FreeDNS Fun
# sudo cp /mnt/data/project/MyTodo/server/deploy/freednsfun-auth.sh /etc/letsencrypt/freednsfun-auth.sh
# 用于 DNS-01 验证时自动添加 TXT 记录
# sudo certbot renew --dry-run --run-deploy-hooks -v

set -e

DOMAIN=$CERTBOT_DOMAIN
TOKEN=$CERTBOT_VALIDATION
RECORDID=1406

# 从环境变量或配置文件读取凭证
# 优先使用环境变量，如果没有则尝试读取配置文件
if [ -z "$FREEDNSFUN_KEY" ] || [ -z "$FREEDNSFUN_TOKEN" ]; then
    if [ -f /etc/letsencrypt/.secrets/freednsfun.ini ]; then
        . /etc/letsencrypt/.secrets/freednsfun.ini
    else
        echo "Error: FREEDNSFUN_KEY and FREEDNSFUN_TOKEN must be set or configured in /etc/letsencrypt/.secrets/freednsfun.ini"
        exit 1
    fi
fi

# 构造记录名：_acme-challenge.{domain}
RECORD_NAME="_acme-challenge"

# API endpoint
API_URL="https://freedns.fun/webapi/ddns"

# 发送请求添加 TXT 记录
REQUEST_URL="${API_URL}?recordid=${RECORDID}&value=${TOKEN}&keyid=${FREEDNSFUN_KEY}&token=${FREEDNSFUN_TOKEN}"

echo "Updating TXT record: ${RECORDID} = ${TOKEN}"
RESPONSE=$(curl -s -X GET "$REQUEST_URL")

if [ "$RESPONSE" = "success" ]; then
    echo "TXT record added successfully"
    # 等待 DNS 传播（FreeDNS Fun 可能需要一些时间）
    sleep 60
    exit 0
else
    echo "Failed to add TXT record. Response: $RESPONSE"
    exit 1
fi
