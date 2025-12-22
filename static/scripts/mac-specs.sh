#!/bin/bash
# MacBook Specification Collector
# Run with: curl -sL https://inventory.truelog.com.sg/specs | bash

SERVER_URL="https://inventory.truelog.com.sg"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

clear
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}${BOLD}           MacBook Specification Collector                  ${NC}${BLUE}║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Collecting system information...${NC}"
echo ""

# Function to print section headers
print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}${BOLD}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Function to print key-value pairs
print_info() {
    printf "  ${GREEN}%-20s${NC} %s\n" "$1:" "$2"
}

# ============================================
# COLLECT ALL SPECS
# ============================================

# Serial Number
SERIAL=$(ioreg -l | grep IOPlatformSerialNumber | awk -F'"' '{print $4}' 2>/dev/null)
if [ -z "$SERIAL" ]; then
    SERIAL=$(system_profiler SPHardwareDataType 2>/dev/null | grep "Serial Number" | awk '{print $NF}')
fi

# Hardware UUID
UUID=$(ioreg -rd1 -c IOPlatformExpertDevice | grep -E 'IOPlatformUUID' | awk '{print $NF}' | tr -d '"' 2>/dev/null)

# Model Identifier
MODEL_ID=$(sysctl -n hw.model 2>/dev/null)
if [ -z "$MODEL_ID" ]; then
    MODEL_ID=$(ioreg -c IOPlatformExpertDevice | grep "model" | head -1 | awk -F'"' '{print $4}' 2>/dev/null)
fi

# Model Name (friendly name)
MODEL_NAME=$(system_profiler SPHardwareDataType 2>/dev/null | grep "Model Name" | sed 's/.*: //')

# CPU
CPU=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)
if [ -z "$CPU" ]; then
    CPU=$(sysctl -n machdep.cpu.brand 2>/dev/null)
fi
if [ -z "$CPU" ]; then
    CHIP=$(system_profiler SPHardwareDataType 2>/dev/null | grep "Chip" | sed 's/.*: //')
    CPU="${CHIP:-Unknown}"
fi

# CPU Cores
CORES=$(sysctl -n hw.ncpu 2>/dev/null)
PCORES=$(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null)
ECORES=$(sysctl -n hw.perflevel1.physicalcpu 2>/dev/null)

if [ -n "$PCORES" ] && [ -n "$ECORES" ]; then
    CPU_CORES="${CORES} (${PCORES}P + ${ECORES}E)"
else
    CPU_CORES="${CORES:-Unknown}"
fi

# GPU
GPU=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Chipset Model" | sed 's/.*: //' | head -1)
if [ -z "$GPU" ]; then
    GPU=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Chip" | sed 's/.*: //' | head -1)
fi
GPU_CORES=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Total Number of Cores" | sed 's/.*: //' | head -1)

# RAM
RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null)
if [ -n "$RAM_BYTES" ]; then
    RAM_GB=$(echo "scale=0; $RAM_BYTES / 1073741824" | bc 2>/dev/null)
    if [ -z "$RAM_GB" ]; then
        RAM_GB=$((RAM_BYTES / 1073741824))
    fi
else
    RAM_GB="Unknown"
fi

# Memory Type
MEM_TYPE=$(system_profiler SPMemoryDataType 2>/dev/null | grep "Type:" | head -1 | sed 's/.*: //')

# Storage
DISK_SIZE=$(diskutil info disk0 2>/dev/null | grep "Disk Size" | awk -F'(' '{print $2}' | awk '{print $1}' 2>/dev/null)
if [ -n "$DISK_SIZE" ]; then
    DISK_GB=$(echo "scale=0; $DISK_SIZE / 1000000000" | bc 2>/dev/null)
    if [ -z "$DISK_GB" ]; then
        DISK_GB=$((DISK_SIZE / 1000000000))
    fi
else
    DISK_GB="Unknown"
fi

DISK_TYPE=$(diskutil info disk0 2>/dev/null | grep "Solid State" | awk '{print $NF}')
if [ "$DISK_TYPE" = "Yes" ]; then
    STORAGE_TYPE="SSD"
else
    STORAGE_TYPE="HDD"
fi

FREE_SPACE=$(df -h / 2>/dev/null | tail -1 | awk '{print $4}')

# macOS Version
if command -v sw_vers &> /dev/null; then
    OS_NAME=$(sw_vers -productName 2>/dev/null)
    OS_VERSION=$(sw_vers -productVersion 2>/dev/null)
    OS_BUILD=$(sw_vers -buildVersion 2>/dev/null)
else
    OS_NAME="macOS"
    OS_VERSION="Unknown"
    OS_BUILD="Unknown"
fi

# Battery
BATTERY_INFO=$(ioreg -r -c AppleSmartBattery 2>/dev/null)
if [ -n "$BATTERY_INFO" ]; then
    CYCLE_COUNT=$(echo "$BATTERY_INFO" | grep '"CycleCount"' | awk '{print $NF}')
    MAX_CAPACITY=$(echo "$BATTERY_INFO" | grep '"MaxCapacity"' | awk '{print $NF}')
    DESIGN_CAPACITY=$(echo "$BATTERY_INFO" | grep '"DesignCapacity"' | awk '{print $NF}')

    if [ -n "$MAX_CAPACITY" ] && [ -n "$DESIGN_CAPACITY" ]; then
        BATTERY_HEALTH=$(echo "scale=1; $MAX_CAPACITY * 100 / $DESIGN_CAPACITY" | bc 2>/dev/null)
    fi
else
    CYCLE_COUNT=""
    BATTERY_HEALTH=""
fi

# Network
WIFI_MAC=$(networksetup -getmacaddress Wi-Fi 2>/dev/null | awk '{print $3}')
ETH_MAC=$(networksetup -getmacaddress Ethernet 2>/dev/null | awk '{print $3}')
if [ "$ETH_MAC" = "not" ]; then
    ETH_MAC=""
fi

# ============================================
# DISPLAY RESULTS
# ============================================
print_header "DEVICE IDENTIFICATION"
print_info "Serial Number" "${SERIAL:-Unknown}"
print_info "Hardware UUID" "${UUID:-Unknown}"

print_header "MODEL INFORMATION"
print_info "Model Name" "${MODEL_NAME:-Unknown}"
print_info "Model Identifier" "${MODEL_ID:-Unknown}"

print_header "PROCESSOR"
print_info "Processor" "${CPU:-Unknown}"
print_info "CPU Cores" "${CPU_CORES}"

print_header "GRAPHICS"
print_info "GPU" "${GPU:-Unknown}"
if [ -n "$GPU_CORES" ]; then
    print_info "GPU Cores" "$GPU_CORES"
fi

print_header "MEMORY"
print_info "Total RAM" "${RAM_GB} GB"
if [ -n "$MEM_TYPE" ]; then
    print_info "Memory Type" "$MEM_TYPE"
fi

print_header "STORAGE"
print_info "Disk Size" "${DISK_GB} GB"
print_info "Disk Type" "${STORAGE_TYPE}"
print_info "Free Space" "${FREE_SPACE:-Unknown}"

print_header "OPERATING SYSTEM"
print_info "OS" "${OS_NAME:-macOS}"
print_info "Version" "${OS_VERSION:-Unknown}"
print_info "Build" "${OS_BUILD:-Unknown}"

if [ -n "$CYCLE_COUNT" ]; then
    print_header "BATTERY"
    print_info "Cycle Count" "$CYCLE_COUNT"
    if [ -n "$BATTERY_HEALTH" ]; then
        print_info "Battery Health" "${BATTERY_HEALTH}%"
    fi
fi

print_header "NETWORK"
print_info "WiFi MAC" "${WIFI_MAC:-Unknown}"
if [ -n "$ETH_MAC" ]; then
    print_info "Ethernet MAC" "$ETH_MAC"
fi

# ============================================
# SUMMARY BOX
# ============================================
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${NC}${BOLD}                    QUICK SUMMARY                            ${NC}${BLUE}║${NC}"
echo -e "${BLUE}╠════════════════════════════════════════════════════════════╣${NC}"
printf "${BLUE}║${NC}  ${GREEN}Serial:${NC} %-50s ${BLUE}║${NC}\n" "${SERIAL:-Unknown}"
printf "${BLUE}║${NC}  ${GREEN}Model:${NC} %-51s ${BLUE}║${NC}\n" "${MODEL_NAME:-$MODEL_ID}"
printf "${BLUE}║${NC}  ${GREEN}CPU:${NC} %-53s ${BLUE}║${NC}\n" "${CPU:-Unknown}"
printf "${BLUE}║${NC}  ${GREEN}RAM:${NC} %-53s ${BLUE}║${NC}\n" "${RAM_GB:-?} GB"
printf "${BLUE}║${NC}  ${GREEN}Storage:${NC} %-49s ${BLUE}║${NC}\n" "${DISK_GB:-?} GB ${STORAGE_TYPE}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================
# SEND TO SERVER
# ============================================
echo -e "${YELLOW}${BOLD}Sending specs to server...${NC}"

# Build JSON payload
JSON_PAYLOAD=$(cat <<EOF
{
    "serial_number": "${SERIAL:-}",
    "hardware_uuid": "${UUID:-}",
    "model_name": "${MODEL_NAME:-}",
    "model_id": "${MODEL_ID:-}",
    "cpu": "${CPU:-}",
    "cpu_cores": "${CPU_CORES:-}",
    "gpu": "${GPU:-}",
    "gpu_cores": "${GPU_CORES:-}",
    "ram_gb": "${RAM_GB:-}",
    "memory_type": "${MEM_TYPE:-}",
    "storage_gb": "${DISK_GB:-}",
    "storage_type": "${STORAGE_TYPE:-}",
    "free_space": "${FREE_SPACE:-}",
    "os_name": "${OS_NAME:-}",
    "os_version": "${OS_VERSION:-}",
    "os_build": "${OS_BUILD:-}",
    "battery_cycles": "${CYCLE_COUNT:-}",
    "battery_health": "${BATTERY_HEALTH:-}",
    "wifi_mac": "${WIFI_MAC:-}",
    "ethernet_mac": "${ETH_MAC:-}"
}
EOF
)

# Send to server
RESPONSE=$(curl -s -X POST "${SERVER_URL}/api/specs/submit" \
    -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD" 2>/dev/null)

# Check response
if echo "$RESPONSE" | grep -q '"success"'; then
    SUBMISSION_ID=$(echo "$RESPONSE" | grep -oE '"id"[[:space:]]*:[[:space:]]*[0-9]+' | grep -oE '[0-9]+')
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ Specs submitted successfully!                           ║${NC}"
    echo -e "${GREEN}║                                                            ║${NC}"
    printf "${GREEN}║${NC}    Submission ID: %-40s ${GREEN}║${NC}\n" "${SUBMISSION_ID}"
    printf "${GREEN}║${NC}    Serial: %-47s ${GREEN}║${NC}\n" "${SERIAL}"
    echo -e "${GREEN}║                                                            ║${NC}"
    echo -e "${GREEN}║  The IT team can now add this device to the inventory.     ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
else
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ✗ Failed to submit specs to server                        ║${NC}"
    echo -e "${RED}║                                                            ║${NC}"
    echo -e "${RED}║  Please copy the information below manually:               ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Serial: ${SERIAL:-Unknown}"
    echo "Model: ${MODEL_NAME:-Unknown}"
    echo "Model ID: ${MODEL_ID:-Unknown}"
    echo "CPU: ${CPU:-Unknown}"
    echo "CPU Cores: ${CPU_CORES:-Unknown}"
    echo "RAM: ${RAM_GB:-Unknown} GB"
    echo "Storage: ${DISK_GB:-Unknown} GB ${STORAGE_TYPE}"
    echo "macOS: ${OS_VERSION:-Unknown} (${OS_BUILD:-Unknown})"
    if [ -n "$CYCLE_COUNT" ]; then
        echo "Battery Cycles: ${CYCLE_COUNT}"
    fi
    echo "WiFi MAC: ${WIFI_MAC:-Unknown}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

echo ""
