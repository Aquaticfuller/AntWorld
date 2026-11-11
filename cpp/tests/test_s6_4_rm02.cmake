string(RANDOM LENGTH 12 ALPHABET 0123456789abcdef nonce)
execute_process(COMMAND "${TEST}" "${MODE}" "${ROOT}/rm02-${MODE}-${nonce}"
    RESULT_VARIABLE result)
if(NOT result EQUAL 0)
    message(FATAL_ERROR "RM-02 ${MODE} failed")
endif()
