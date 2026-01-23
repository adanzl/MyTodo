#!/usr/bin/env sh

# FreeDNS Fun DNS API Plugin
# URL: https://freedns.fun/
#
# This plugin is used for automatically adding and removing TXT records for DNS-01 challenge
# using FreeDNS Fun's API.
#
# Instructions:
# 1. Set the environment variables FREEDNS_User and FREEDNS_Token with your FreeDNS Fun credentials.
# 2. Use the --dns dns_freednsfun parameter with acme.sh to issue a certificate.
#
# Example:
# export FREEDNS_User="your_username"
# export FREEDNS_Token="your_token"
# ./acme.sh --issue --dns dns_freednsfun -d yourdomain.com -d *.yourdomain.com

# API endpoint for FreeDNS Fun
FREEDNSFUN_API="https://freedns.fun/zone/ssl"

# Initialize the plugin
dns_freednsfun_init() {
  _info "Initializing FreeDNS Fun DNS plugin"
  # Check if required environment variables are set
  if [ -z "${FREEDNSFUN_KEY}" ] || [ -z "${FREEDNSFUN_TOKEN}" ]; then
    _err "Error: FREEDNS_User and FREEDNS_Token environment variables must be set."
    return 1
  fi
  return 0
}

# Add a TXT record for the specified domain and subdomain
dns_freednsfun_add() {
  _info "Adding TXT record for domain: $1"
  _debug "value: $1"
 # _debug "TXT value: $3"

  # Extract the main domain and construct the full subdomain
 # main_domain=$(echo "$1" | awk -F '.' '{print $(NF-1)"."$NF}')
  
  # Construct the API request URL
  request_url="${FREEDNSFUN_API}/addrecord?records=$1&value=$2&key=${FREEDNSFUN_KEY}&token=${FREEDNSFUN_TOKEN}"
 _info "请求地址:$request_url"
  # Send the GET request to add the TXT record
  response=$(curl -s -X GET "$request_url")
  _info "curl:$request"
   #response="success"
 # 检查响应是否为 "success"
  if [ "$response" = "success" ]; then
    _debug "TXT 记录添加成功。"
    return 0
  else
    _err "添加 TXT 记录失败。"
    return 1
  fi
}

# Remove the TXT record for the specified domain and subdomain
dns_freednsfun_rm() {
  _info "Removing TXT record for domain: $1"
  # Construct the API request URL
  request_url="${FREEDNSFUN_API}/delrecord?records=$1&key=${FREEDNSFUN_KEY}&token=${FREEDNSFUN_TOKEN}"

  # Send the GET request to remove the TXT record
  response=$(curl -s -X GET "$request_url")
  #response="success"
  # Check if the request was successful
  # 检查响应是否为 "success"
  if [ "$response" = "success" ]; then
    _debug "TXT 记录删除成功。"
    return 0
  else
    _err "删除 TXT 记录失败。"
    return 1
  fi
}