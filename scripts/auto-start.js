#!/usr/bin/env node

/**
 * Auto-detection script for environment-specific startup
 * Automatically detects Windows, Codespaces, or Linux and runs appropriate commands
 */

const { execSync } = require('child_process');
const os = require('os');

function detectEnvironment() {
    // Check if running in GitHub Codespaces
    if (process.env.CODESPACES === 'true' || process.env.CODESPACE_NAME) {
        return 'codespaces';
    }
    
    // Check if running on Windows
    if (os.platform() === 'win32') {
        return 'windows';
    }
    
    // Default to Linux/Unix
    return 'linux';
}

function runCommand(command) {
    console.log(`🚀 Running: ${command}`);
    try {
        execSync(command, { stdio: 'inherit' });
    } catch (error) {
        console.error(`❌ Error running command: ${command}`);
        console.error(error.message);
        process.exit(1);
    }
}

function main() {
    const env = detectEnvironment();
    
    console.log('🔍 Environment Detection:');
    console.log(`📍 Detected environment: ${env}`);
    console.log(`🖥️  Platform: ${os.platform()}`);
    console.log(`📂 Working directory: ${process.cwd()}`);
    console.log('');
    
    switch (env) {
        case 'codespaces':
            console.log('🌐 Starting in GitHub Codespaces mode...');
            runCommand('npm run dev:codespaces');
            break;
            
        case 'windows':
            console.log('🪟 Starting in Windows mode...');
            runCommand('npm run dev:windows');
            break;
            
        case 'linux':
            console.log('🐧 Starting in Linux mode...');
            runCommand('npm run dev');
            break;
            
        default:
            console.error(`❌ Unknown environment: ${env}`);
            process.exit(1);
    }
}

if (require.main === module) {
    main();
}

module.exports = { detectEnvironment };