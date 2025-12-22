#!/bin/bash
# MacBook Specification Collector
# Run with: curl -sL yourserver.com/specs | bash

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
# SERIAL NUMBER
# ============================================
print_header "DEVICE IDENTIFICATION"

SERIAL=$(ioreg -l | grep IOPlatformSerialNumber | awk -F'"' '{print $4}' 2>/dev/null)
if [ -z "$SERIAL" ]; then
    SERIAL=$(system_profiler SPHardwareDataType 2>/dev/null | grep "Serial Number" | awk '{print $NF}')
fi
print_info "Serial Number" "${SERIAL:-Unknown}"

# Hardware UUID
UUID=$(ioreg -rd1 -c IOPlatformExpertDevice | grep -E 'IOPlatformUUID' | awk '{print $NF}' | tr -d '"' 2>/dev/null)
print_info "Hardware UUID" "${UUID:-Unknown}"

# ============================================
# MODEL INFORMATION
# ============================================
print_header "MODEL INFORMATION"

# Model Identifier
MODEL_ID=$(sysctl -n hw.model 2>/dev/null)
if [ -z "$MODEL_ID" ]; then
    MODEL_ID=$(ioreg -c IOPlatformExpertDevice | grep "model" | head -1 | awk -F'"' '{print $4}' 2>/dev/null)
fi
print_info "Model Identifier" "${MODEL_ID:-Unknown}"

# Model Name (friendly name)
MODEL_NAME=$(system_profiler SPHardwareDataType 2>/dev/null | grep "Model Name" | sed 's/.*: //')
print_info "Model Name" "${MODEL_NAME:-Unknown}"

# Model Year (if available)
MODEL_YEAR=$(system_profiler SPHardwareDataType 2>/dev/null | grep "Model Identifier" | sed 's/.*: //')
print_info "Model ID" "${MODEL_YEAR:-Unknown}"

# ============================================
# PROCESSOR (CPU)
# ============================================
print_header "PROCESSOR"

# CPU Brand String
CPU=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)
if [ -z "$CPU" ]; then
    # For Apple Silicon
    CPU=$(sysctl -n machdep.cpu.brand 2>/dev/null)
fi
if [ -z "$CPU" ]; then
    # Fallback for M-series
    CHIP=$(system_profiler SPHardwareDataType 2>/dev/null | grep "Chip" | sed 's/.*: //')
    CPU="${CHIP:-Unknown}"
fi
print_info "Processor" "${CPU:-Unknown}"

# CPU Cores
CORES=$(sysctl -n hw.ncpu 2>/dev/null)
PCORES=$(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null)
ECORES=$(sysctl -n hw.perflevel1.physicalcpu 2>/dev/null)

if [ -n "$PCORES" ] && [ -n "$ECORES" ]; then
    print_info "CPU Cores" "${CORES} total (${PCORES}P + ${ECORES}E)"
else
    print_info "CPU Cores" "${CORES:-Unknown}"
fi

# ============================================
# GPU
# ============================================
print_header "GRAPHICS"

GPU=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Chipset Model" | sed 's/.*: //' | head -1)
if [ -z "$GPU" ]; then
    GPU=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Chip" | sed 's/.*: //' | head -1)
fi
GPU_CORES=$(system_profiler SPDisplaysDataType 2>/dev/null | grep "Total Number of Cores" | sed 's/.*: //' | head -1)

print_info "GPU" "${GPU:-Unknown}"
if [ -n "$GPU_CORES" ]; then
    print_info "GPU Cores" "$GPU_CORES"
fi

# ============================================
# MEMORY (RAM)
# ============================================
print_header "MEMORY"

# Total RAM in GB
RAM_BYTES=$(sysctl -n hw.memsize 2>/dev/null)
if [ -n "$RAM_BYTES" ]; then
    RAM_GB=$(echo "scale=0; $RAM_BYTES / 1073741824" | bc 2>/dev/null)
    if [ -z "$RAM_GB" ]; then
        RAM_GB=$((RAM_BYTES / 1073741824))
    fi
    print_info "Total RAM" "${RAM_GB} GB"
else
    print_info "Total RAM" "Unknown"
fi

# Memory Type
MEM_TYPE=$(system_profiler SPMemoryDataType 2>/dev/null | grep "Type:" | head -1 | sed 's/.*: //')
if [ -n "$MEM_TYPE" ]; then
    print_info "Memory Type" "$MEM_TYPE"
fi

# ============================================
# STORAGE
# ============================================
print_header "STORAGE"

# Get main disk info
DISK_SIZE=$(diskutil info disk0 2>/dev/null | grep "Disk Size" | awk -F'(' '{print $2}' | awk '{print $1}' 2>/dev/null)
if [ -n "$DISK_SIZE" ]; then
    DISK_GB=$(echo "scale=0; $DISK_SIZE / 1000000000" | bc 2>/dev/null)
    if [ -z "$DISK_GB" ]; then
        DISK_GB=$((DISK_SIZE / 1000000000))
    fi
    print_info "Disk Size" "${DISK_GB} GB"
fi

# Disk type
DISK_TYPE=$(diskutil info disk0 2>/dev/null | grep "Solid State" | awk '{print $NF}')
if [ "$DISK_TYPE" = "Yes" ]; then
    print_info "Disk Type" "SSD"
else
    print_info "Disk Type" "HDD"
fi

# Free space
FREE_SPACE=$(df -h / 2>/dev/null | tail -1 | awk '{print $4}')
print_info "Free Space" "${FREE_SPACE:-Unknown}"

# ============================================
# macOS VERSION
# ============================================
print_header "OPERATING SYSTEM"

if command -v sw_vers &> /dev/null; then
    OS_NAME=$(sw_vers -productName 2>/dev/null)
    OS_VERSION=$(sw_vers -productVersion 2>/dev/null)
    OS_BUILD=$(sw_vers -buildVersion 2>/dev/null)

    print_info "OS" "${OS_NAME:-macOS}"
    print_info "Version" "${OS_VERSION:-Unknown}"
    print_info "Build" "${OS_BUILD:-Unknown}"
else
    print_info "OS" "Unknown (Recovery Mode?)"
fi

# ============================================
# BATTERY (if laptop)
# ============================================
BATTERY_INFO=$(ioreg -r -c AppleSmartBattery 2>/dev/null)
if [ -n "$BATTERY_INFO" ]; then
    print_header "BATTERY"

    CYCLE_COUNT=$(echo "$BATTERY_INFO" | grep '"CycleCount"' | awk '{print $NF}')
    MAX_CAPACITY=$(echo "$BATTERY_INFO" | grep '"MaxCapacity"' | awk '{print $NF}')
    DESIGN_CAPACITY=$(echo "$BATTERY_INFO" | grep '"DesignCapacity"' | awk '{print $NF}')

    if [ -n "$CYCLE_COUNT" ]; then
        print_info "Cycle Count" "$CYCLE_COUNT"
    fi

    if [ -n "$MAX_CAPACITY" ] && [ -n "$DESIGN_CAPACITY" ]; then
        HEALTH=$(echo "scale=1; $MAX_CAPACITY * 100 / $DESIGN_CAPACITY" | bc 2>/dev/null)
        if [ -n "$HEALTH" ]; then
            print_info "Battery Health" "${HEALTH}%"
        fi
    fi
fi

# ============================================
# NETWORK
# ============================================
print_header "NETWORK"

# WiFi MAC Address
WIFI_MAC=$(networksetup -getmacaddress Wi-Fi 2>/dev/null | awk '{print $3}')
print_info "WiFi MAC" "${WIFI_MAC:-Unknown}"

# Ethernet MAC Address
ETH_MAC=$(networksetup -getmacaddress Ethernet 2>/dev/null | awk '{print $3}')
if [ -n "$ETH_MAC" ] && [ "$ETH_MAC" != "not" ]; then
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
printf "${BLUE}║${NC}  ${GREEN}Storage:${NC} %-49s ${BLUE}║${NC}\n" "${DISK_GB:-?} GB SSD"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================
# COPY-PASTE FRIENDLY OUTPUT
# ============================================
echo -e "${YELLOW}${BOLD}Copy-Paste Format (for inventory system):${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Serial: ${SERIAL:-Unknown}"
echo "Model: ${MODEL_NAME:-Unknown}"
echo "Model ID: ${MODEL_ID:-Unknown}"
echo "CPU: ${CPU:-Unknown}"
echo "CPU Cores: ${CORES:-Unknown}"
echo "RAM: ${RAM_GB:-Unknown} GB"
echo "Storage: ${DISK_GB:-Unknown} GB"
echo "macOS: ${OS_VERSION:-Unknown} (${OS_BUILD:-Unknown})"
if [ -n "$CYCLE_COUNT" ]; then
    echo "Battery Cycles: ${CYCLE_COUNT}"
fi
echo "WiFi MAC: ${WIFI_MAC:-Unknown}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}Done! Copy the information above into your inventory system.${NC}"
echo ""
