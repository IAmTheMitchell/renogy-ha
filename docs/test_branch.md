# Testing a New Version of Renogy-HA

You can help test a new version of Renogy-HA by installing it in your Home Assistant instance and providing feedback. Be aware that test versions may have unforseen issues.

## Installation

1. Open **Developer tools** from the Home Assistant sidebar.
2. Select the **Actions** tab.
3. Select **Install Update** in the Action dropdown.
4. Select **Update Renogy (update.renogy_update)** as the Target.
5. Enter the **test branch** as the Version.

Home Assistant may give you a notification to re-install the main branch version. Decline the notification, or it will overwrite the test version. When a newer version is released with the fix or feature you are testing, the notification will display again, and you can update.

![Example screenshot showing how to update to a specific branch.](docs/test_branch.png)
