Lineage 2 Automation Policy
Developer: NCSoft
Last Updated: August 29, 2023
Overview
NCSoft permits limited use of automated keyboard and mouse inputs in Lineage 2 for specific purposes, such as market monitoring and accessibility, to enhance player experience while maintaining game integrity. This policy outlines the conditions under which automation is allowed.
Scope
This policy applies to Lineage 2 (PC version, all regions). Automation is permitted only for non-competitive, single-player features, such as monitoring in-game market data (e.g., auction house or trade windows). Automation in competitive modes (e.g., PvP, sieges) or for unattended gameplay is strictly prohibited.
Approved Automation
Automated keyboard and mouse inputs are explicitly allowed for:

Market Monitoring: Scripts to monitor auction house or trade window data, including item quantities, prices, and trader information, using tools like pyautogui or Arduino-based HID emulation.
Accessibility: To assist players with disabilities in navigating menus or performing repetitive tasks.
Modding/Testing: For developers creating approved add-ons within NCSoft’s modding guidelines.

Conditions for Use

Non-Competitive Use: Automation must not provide gameplay advantages (e.g., auto-farming, auto-trading, or exploiting market mechanics).
Single-Player Features: Limited to interactions with the auction house, trade windows, or other non-PvP/PvE systems.
Approved Tools: Tools like Python (pyautogui, pyserial), Arduino (Keyboard.h, Mouse.h), and OCR (pytesseract) are permitted if they comply with this policy.
Rate Limits: Automated inputs must include delays (e.g., 100ms between actions) to mimic human interaction and avoid server strain.
Registration: Players must register automation tools with NCSoft via support@ncsoft.com for approval.

Implementation Guidelines

Input Simulation: Use human-like delays (e.g., 100-200ms between keypresses/clicks).
Supported Actions: Navigation (arrow keys), interaction (Enter, Esc), text input (e.g., search queries), and mouse clicks in auction/trade windows.
Data Collection: OCR-based scanning of trade windows is allowed for extracting item names, quantities, and prices.
Example: A Python script using pyautogui to scan the auction house or an Arduino sketch to emulate mouse clicks for navigation.

Enforcement
Violations (e.g., automation in PvP, unattended gameplay, or market manipulation) will result in immediate account suspension or permanent bans. NCSoft monitors automation via client-side detection systems.
Contact
To register automation tools or for inquiries, contact support@ncsoft.com or visit https://www.lineage2.com/support.