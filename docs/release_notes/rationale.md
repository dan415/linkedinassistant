
<h2> Release Notes </h2>

<h3> v1.0.3 </h3>

This release intends to solve some bugs that were not detected on the previous release, related to running the
program as a Windows service.

- Changed Couroutine approach to Stoppable thread approach for running the tasks. This is because the Couroutine approach
  was not working as expected when running the program as a Windows service, and subprocesses created by the tasks were not being able to start.
- Added a new config parameter called "base_path" to `telegram/suggestions/config.json`. I had not realized this parameters was hardcoded in the previous version.
- Fixed bug when resolving absolute paths defined in configs when running the program as a Windows service.