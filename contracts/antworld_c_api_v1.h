#ifndef ANTWORLD_C_API_V1_H
#define ANTWORLD_C_API_V1_H
/*
 * Contract draft only; implementations are intentionally absent.
 * v0.8 design handoff. No STL/C++ exceptions through this boundary.
 * First native implementation is a later Codex milestone, NOT S0.
 */
#include <stdint.h>

#if defined(_WIN32)
  #if defined(AW_BUILD_DLL)
    #define AW_API __declspec(dllexport)
  #else
    #define AW_API __declspec(dllimport)
  #endif
  #define AW_CALL __cdecl
#else
  #define AW_API
  #define AW_CALL
#endif

#ifdef __cplusplus
extern "C" {
#endif

#define AW_API_VERSION_V1 (1u)

typedef struct AW_WorldOpaque* AW_WorldHandle;
typedef struct AW_SnapshotOpaque* AW_SnapshotHandle;

/* Fixed-width ABI result; C enum size is compiler-dependent. */
typedef int32_t AW_Result;
enum {
    AW_OK = 0,
    AW_ERR_INVALID_ARG = 1,
    AW_ERR_INVALID_HANDLE = 2,
    AW_ERR_VERSION = 3,
    AW_ERR_BUFFER_TOO_SMALL = 4,
    AW_ERR_NOT_FOUND = 5,
    AW_ERR_CONFLICT = 6,
    AW_ERR_INTERNAL = 255
};

typedef struct AW_WorldId {
    uint64_t high;
    uint64_t low;
} AW_WorldId;

typedef struct AW_WorldCreateDesc {
    uint32_t struct_size;
    uint32_t api_version;
    AW_WorldId world_id;
    uint64_t seed;
} AW_WorldCreateDesc;

typedef struct AW_SnapshotInfo {
    uint32_t struct_size;
    uint32_t api_version;
    AW_WorldId world_id;
    int64_t sim_time_ms;
    uint64_t world_revision;
    uint64_t geometry_revision;
} AW_SnapshotInfo;

typedef struct AW_AntRenderState {
    uint32_t struct_size;
    uint32_t api_version;
    uint64_t ant_id;
    uint64_t colony_id;
    double x_m;
    double y_m;
    double z_m;
    float heading_rad;
    uint32_t life_stage;
    uint32_t visual_action;
} AW_AntRenderState;

/* No create/destroy allocations cross the boundary except opaque handles. */
AW_API AW_Result AW_CALL aw_world_create(const AW_WorldCreateDesc* desc,
                                        AW_WorldHandle* out_world);
AW_API AW_Result AW_CALL aw_world_destroy(AW_WorldHandle world);
AW_API AW_Result AW_CALL aw_world_advance_to(AW_WorldHandle world,
                                            int64_t target_time_ms);
AW_API AW_Result AW_CALL aw_snapshot_acquire(AW_WorldHandle world,
                                            AW_SnapshotHandle* out_snapshot);
AW_API AW_Result AW_CALL aw_snapshot_get_info(AW_SnapshotHandle snapshot,
                                             AW_SnapshotInfo* out_info);
/* When capacity=0, pass out_ants=NULL; out_required receives count. */
AW_API AW_Result AW_CALL aw_snapshot_copy_ants(AW_SnapshotHandle snapshot,
                                             AW_AntRenderState* out_ants,
                                             uint32_t capacity,
                                             uint32_t* out_required);
AW_API AW_Result AW_CALL aw_snapshot_release(AW_SnapshotHandle snapshot);

#ifdef __cplusplus
}
#endif
#endif /* ANTWORLD_C_API_V1_H */
