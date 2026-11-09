# Fresh evidence directories make repeated CTest runs preserve earlier output.
string(RANDOM LENGTH 12 ALPHABET 0123456789abcdef suffix)
if(MODE STREQUAL "NUTRITION")
    set(arguments smoke)
else()
    set(arguments 1)
endif()
execute_process(COMMAND "${APP}" "${OUTPUT_DIR}-${suffix}" ${arguments}
    RESULT_VARIABLE result OUTPUT_VARIABLE stdout ERROR_VARIABLE stderr)
if(NOT result EQUAL 0)
    message(FATAL_ERROR "Observer failed (${result}): ${stdout}\n${stderr}")
endif()
message(STATUS "${stdout}")
