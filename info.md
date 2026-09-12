## Smart Garage Door Integration

Transform your existing garage door sensors and switches into intelligent garage door entities with proper state management and control.

### What it does:
- Creates smart sensor entities that track garage door states (open, closed, opening, unavailable)
- Generates proper cover entities for Home Assistant garage door control
- Implements safety logic to prevent invalid operations
- Supports multiple garage doors with individual configuration
- Provides "opening" state detection based on timing after switch activation

### Requirements:
- Binary sensor for detecting door open state
- Binary sensor for detecting door closed state  
- Switch or light entity to control garage door opener
- Home Assistant 2025.8.0 or newer

### Configuration:
Add each garage door through **Settings → Devices & Services → Add Integration**, picking your
sensor and toggle entities. Reconfigure or tune it later from the same integration entry.

### Perfect for:
- DIY garage door automation setups
- Converting basic sensors into proper garage door entities
- Multiple garage door management
- Integration with existing Home Assistant automations and dashboards 