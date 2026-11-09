string(RANDOM LENGTH 12 ALPHABET 0123456789abcdef suffix)
execute_process(COMMAND "${APP}" "${OUTPUT_DIR}-${suffix}" smoke
    RESULT_VARIABLE result OUTPUT_VARIABLE stdout ERROR_VARIABLE stderr)
if(NOT result EQUAL 0)
    message(FATAL_ERROR "Long-term durable experiment failed: ${stdout}\n${stderr}")
endif()
message(STATUS "${stdout}")
