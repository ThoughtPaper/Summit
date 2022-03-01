# Summit
Analysis and reporting tool for Scouts|Terrain

Before use the settings file should be updated as follows:

 * SMTP mail server details (server, port, user, password)
 * Terrain profile (Unit name, Unit ID, Terrain user/password and recipient email addresses)

Notes:
 * The Terrain user is created by concatenating the branch (eg. VIC) with a '-' and the Scout ID
 * The Unit ID can be found by running the browser DEV Tools (F12) while viewing the Group Life page, simply check the response to /units?limit=999&force=0 request and choose the required unit
 * there can be many profiles set up to run for say each unit in the group (Joeys, Cubs, Scouts etc), if this is required it is best to use a specific user for each profile that has been granted unit council access as the approvals will only be correct if the user has unit council permissions to that unit
 * more than one recipient address can be specified
