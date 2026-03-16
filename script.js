// Global state
let agentsData = [];
let commandCount = 0;

// Update live clock
function updateClock() {
    const clockElement = document.getElementById('liveClock');
    const now = new Date();
    const timeString = now.toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    clockElement.textContent = timeString;
}

// Add terminal message
function addTerminalMessage(message, type = 'system') {
    const terminal = document.getElementById('terminal');
    const line = document.createElement('div');
    line.className = 'terminal-line';
    
    const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
    const prefix = type === 'command' ? '[COMMAND]' : 
                   type === 'error' ? '[ERROR]' : '[SYSTEM]';
    
    line.textContent = `[${timestamp}] ${prefix} ${message}`;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
}

// Update statistics
function updateStats() {
    const totalAgents = agentsData.length;
    const activeAgents = agentsData.filter(agent => 
        agent.status.toLowerCase() === 'active' || agent.status.toLowerCase() === 'online'
    ).length;
    
    document.getElementById('totalAgents').textContent = totalAgents;
    document.getElementById('activeAgents').textContent = activeAgents;
    document.getElementById('commandsExecuted').textContent = commandCount;
    document.getElementById('alerts').textContent = '0';
}

// Fetch agents from API
async function fetchAgents() {
    const tableBody = document.getElementById('agentsTableBody');
    
    try {
        const response = await fetch('http://localhost:5000/agents');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        agentsData = await response.json();
        
        // Clear table
        tableBody.innerHTML = '';
        
        if (agentsData.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="loading-cell">No agents connected</td>
                </tr>
            `;
            updateStats();
            return;
        }
        
        // Populate table
        agentsData.forEach(agent => {
            const row = document.createElement('tr');
            const isOnline = agent.status.toLowerCase() === 'active' || 
                           agent.status.toLowerCase() === 'online';
            const statusClass = isOnline ? 'status-online' : 'status-offline';
            const statusText = isOnline ? '● ONLINE' : '○ OFFLINE';
            
            row.innerHTML = `
                <td>${agent.agent_id}</td>
                <td>${agent.hostname}</td>
                <td>${agent.username}</td>
                <td>${agent.os}</td>
                <td class="${statusClass}">${statusText}</td>
            `;
            
            tableBody.appendChild(row);
        });
        
        updateStats();
        addTerminalMessage(`Loaded ${agentsData.length} agent(s) successfully`);
        
    } catch (error) {
        console.error('Error fetching agents:', error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="loading-cell">
                    <span style="color: #ff4d4d;">⚠ Failed to connect to API server</span>
                </td>
            </tr>
        `;
        addTerminalMessage(`Failed to fetch agents: ${error.message}`, 'error');
    }
}

// Send command
function sendCommand() {
    const input = document.getElementById('commandInput');
    const command = input.value.trim();
    
    if (command === '') {
        return;
    }
    
    addTerminalMessage(command, 'command');
    addTerminalMessage(`Command executed successfully`);
    
    commandCount++;
    updateStats();
    
    // Clear input
    input.value = '';
}

// Clear terminal
function clearTerminal() {
    const terminal = document.getElementById('terminal');
    terminal.innerHTML = '';
    addTerminalMessage('Terminal cleared');
}

// Navigation handling
function handleNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            
            const page = item.getAttribute('data-page');
            addTerminalMessage(`Navigated to ${page} section`);
        });
    });
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing C2 Control Center...');
    
    // Start clock
    updateClock();
    setInterval(updateClock, 1000);
    
    // Initial agent fetch
    fetchAgents();
    
    // Auto-refresh agents every 30 seconds
    setInterval(fetchAgents, 30000);
    
    // Event listeners
    const sendBtn = document.getElementById('sendBtn');
    const commandInput = document.getElementById('commandInput');
    const refreshBtn = document.getElementById('refreshBtn');
    const clearBtn = document.getElementById('clearBtn');
    
    if (sendBtn) {
        sendBtn.addEventListener('click', sendCommand);
    }
    
    if (commandInput) {
        commandInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendCommand();
            }
        });
    }
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            addTerminalMessage('Manually refreshing agents...');
            fetchAgents();
        });
    }
    
    if (clearBtn) {
        clearBtn.addEventListener('click', clearTerminal);
    }
    
    // Setup navigation
    handleNavigation();
    
    // Initial stats
    updateStats();
    
    console.log('C2 Control Center initialized successfully');
});
