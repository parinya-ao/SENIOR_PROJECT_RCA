#include "task.h"
#include <assert.h>
class RestartTask : public Task {
 public:
    unsigned entries=0,completions=0;
    const char* GetName() override { return "restart-test"; }
    TASK(Run()) override {
        TASK_BEGIN();
        ++entries;
        TASK_YIELD();
        ++completions;
        TASK_END();
    }
};
int main() {
    RestartTask task;
    task.Run();assert(task.entries==1 && task.completions==0);
    task.Pause();task.SetWakeupTime(100);task.Restart();
    assert(!task.IsPaused() && task.GetWakeupTime()==0);
    task.Run();assert(task.entries==2 && task.completions==0);
    task.Run();assert(task.entries==2 && task.completions==1);
}
