# Disclaimer
------------------------------------------------------------------------------
This repository is a scientific product and is not official communication of the National Oceanic and Atmospheric Administration (NOAA), or the United States Department of Commerce (DOC). All NOAA GitHub project code is provided on an ‘as is’ basis and the user assumes responsibility for its use. Any claims against the Department of Commerce or Department of Commerce bureaus stemming from the use of this GitHub project will be governed by all applicable federal law. Any reference to specific commercial products, processes, or services by service mark, trademark, manufacturer, or otherwise, does not constitute or imply their endorsement, recommendation, or favoring by the Department of Commerce. The Department of Commerce seal and logo, or the seal and logo of a DOC bureau, shall not be used in any manner to imply endorsement of any commercial product or activity by DOC or the United States Government.

-------------------------------------------------------------------------------
# IWXXM-US Modelling
This repository hosts an [Enterprise Architect](https://sparxsystems.com/enterprise-architect/index.html) (EA) project file containing the IWXXM-US Unified Modeling Language (UML) model. From this project file, IWXXM-US [schemas](https://nws.weather.gov/schemas/IWXXM-US) and documentation are created from Enterprise Architect. In addition to the project file, a python script with associated configuration files, specific to each product schema, are needed to 'post-process' the EA output to generate the final form of the schemas before posting to the IWXXM-US website.

-------------------------------------------------------------------------------
# Prerequisites
[Enterprise Architect](https://sparxsystems.com/enterprise-architect/index.html) is required to utilize the project file. A Python interpreter (v3.7 or better) is needed to run a script that post-processes the schemas generated from the EA application.

## Cloning
-------------------------------------------------------------------------------
The following instructions assume you are using a computer with a Unix-based operating system. Installing this software on other operating systems may require some adjustments. 

	$ cd /path/to/install/directory
	$ git clone git@github.com:NOAA-MDL/iwxxm-us-modelling.git

-------------------------------------------------------------------------------
# IWXXM-US Schema Generation
From the EA application, and after the IWXXM-US UML project file is opened, the schema files are created from the Toolbar 'Specialize->GML->Generate GML Application Schema.' Please make sure the resulting schema files are written to the EA/ sub-directory.

Once EA has written the schema files to the EA/ sub-directory, run the python script in py/, postProcessEA.py, with a schema configuration file as an argument. The resulting output is written to the /schemas sub-directory. The results in schemas/ should be compared to what is posted on the IWXXM-US website to verify the desired changes.

Further instruction on EA's UML modelling tools is far beyond the scope of this README.

-------------------------------------------------------------------------------
# IWXXM-US Changes
Since the EA project file is a propritary binary format, it is not possible to use some of Git features on the file. Comparisons and merging tools will not work, for instance. Hence GitHub issues associated with the EA project file must provide *precise* details on all changes to the UML model and resulting schema changes in order to verify the changes are as intended before posting to the public website.
