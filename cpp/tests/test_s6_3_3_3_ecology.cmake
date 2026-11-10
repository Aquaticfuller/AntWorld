string(RANDOM LENGTH 12 ALPHABET 0123456789abcdef nonce)
execute_process(COMMAND "${CLI}" "${ROOT}/closure-${MODE}-${nonce}" "${MODE}"
                RESULT_VARIABLE result OUTPUT_VARIABLE output ERROR_VARIABLE error)
if(NOT result EQUAL 0)
    message(FATAL_ERROR "${output}\n${error}")
endif()
