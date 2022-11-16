# ----------------------------------
#
#	Manakin camera motion analysis
#	Working scripts 2022-11-09
#   L. U. Taylor 
#	README
#
# ----------------------------------

edit ~/.bash_aliases with:
alias corMov="/path/to/motionDetection.py"

This program allows for semi-automated motion detection of manakin displays.
The vision analysis is built using OpenCV for Python.

Program process:
	1. Read-in a single video file or an entire directory of files.
		Manually input your name or observer code and the date
		on which the videos were taken.

		NOTE ffmpeg may print "Invalid UE golomb code" warnings
		while frames are being read in. This does not affect
		the program and, while annoying, should be ignored.

	2. Resize input frames, convert to grayscale, and blur.

	3. Determine motion via velocity across a window of three frames.

	4. Threshold and score motion to determine motion periods. Store clips in a 
		temporary video file to be read back in the next step.
		
	5. After a prompt, allow the user to survey motion clips, reading back from the 
		storage file and clearing those that do not feature a bird. The program 
		should contain many false positives but (no guarantees) no false negatives.
		Each 2 sec clip will be displayed in a separate window. After the clip finishes,
		you will be given a prompt. If you would like to keep the clip time on record
		(i.e., it has a bird in it), type 'y' and then press enter. If you would
		like to clear the clip from the list (i.e., it has no bird in it), type 'c'
		and then press enter. If you would like to re-play the clip, simply press enter.
		Any other input (including, e.g., 'Y', "YC", "ADSF"), will replay the clip.

	6. When all the clips of a single file are  a final list of times 
		(H:MM:SS.SS) at which motin begins.

		NOTE Due to calculations from frames->seconds, motion occuring
		at the end of the video may be marked up to ~10s early than the 
		motion actually occurs in the video. The clips displayed within
		the program will still be accurate.

	7. Metadata will be written to a "motiondetection_metadata.csv" file in the
		working directory.

		OPTIONAL: append final list of times to an output file


Running the program:
	This program was built on WSL (Ubuntu) in Python 3.9.12 using OpenCV 3.3.0-dev.
	Other versions may interfere with video I/O due to Codec problems.
	OpenCV is terrible with version differences, so watch out.
	
	1. On a computer with OpenCV and Python3.9 installed, open a terminal window.
	2. Navigate (cd) to the directory that contains the src/ folder.
	3. Compile and run the program with the commands:
		python src/motionDetection.py [-w][-h] inFile [-d] [-o outfile]
		
		inFile is required, and must be the file path to the input video

		[-d] is required if the inFile location is a DIRECTORY rather than a single file.
		[-w] is optional. Show the thresholded motion images as the program runs. Fun but slow.
		[-o] is optional. Send it a file path to write the final output message to file.

		[-h] is optional, and displays parameter help without running the program.

	EXAMPLES:
		Example on an entire directory with output:
		python3 src/motionDetection.py Test_Footage/ -d -o Results/test_results.txt

		Example with a single file with output:
		python3 src/motionDetection.py Test_Footage/Male_Female_Brits.MP4 -o Results/test_results.txt

		Example with no output, an entire directory, and watching the frames for motion:
		python3 src/motionDetection.py -w Test_Footage/ -d 
	



		
