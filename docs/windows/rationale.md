
<h2> Windows Service </h2>

The LinkedinAssistantService class is designed to run the LinkedIn Assistant as a Windows Service.

This service ensures that the LinkedIn Assistant runs continuously in the background and 
can be managed by the Windows Service Manager. 
It includes methods for initializing the service, 
handling accepted controls, 
and running the service in a threaded environment. 
The service can automatically restart on failure and perform cleanup operations when stopped.

Basically, the service is a wrapper around the LinkedIn Assistant main module.

This service is meant to be installed and executed as the user's account, and not with local system account, 
as it requires accessing Windows Credential Manager to store and retrieve the Hashicorp Vault credentials
(which cannot be accessed by the local system account).