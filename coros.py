import signal
import time
import queue

class Queue(queue.Queue):
    def get(self, *args, **kwargs):
        # print("GET...")
        item = super().get(*args, **kwargs)
        # print(f"GET: {item}")
        return item
    
    def put(self, item):
        # print(f"PUT...")
        super().put(item)
        # print(f"PUT: {item}")

class Sched:
    def __init__(self, interval = 0.5):
        self.tasks = []
        self.running = False
        self.interval = interval

    def run_all(self):
        self._set_handler()
        self.running = True
        tid, t = self.get_next_runnable()
        while t and self.running:
            self.run_job(tid)
            tid, t = self.get_next_runnable()
            
        self.running = False
        self._unset_handler()

    def run_job(self, tid):
        print(f"RUN: {tid}")
        t = self.tasks[tid]
        t.run()
        if t.exception:
            print(f"task #{tid} failed with exception: {t.exception}")
        if t.done:
            print(f"task #{tid} complete")

    def get_next_runnable(self):
        for tid, t in enumerate(self.tasks):
            if t.ready:
                return tid, t
        return None, None

    def add(self, *tasks):
        self.tasks += tasks

    def handler(self, sig, frame):
        # print("handler called")
        tid, t = self.get_next_runnable()
        if t:
            self.run_job(tid)

    def _set_handler(self):
        signal.signal(signal.SIGALRM, self.handler)
        signal.setitimer(signal.ITIMER_REAL, self.interval, self.interval)

    def _unset_handler(self):
        signal.setitimer(signal.ITIMER_REAL, 0, 0)

class Task:
    def __init__(self, body):
        self.body = body
        self.done = False
        self.exception = None
        self.ready = True
        self.result = []
        self.out_pipe = None
        self.in_pipe = None
        self.started = False

    def run(self):
        self.ready = False
        try:
            if self.in_pipe:
                pass
            else:
                self.started = True
                self.result = self.body()
        except Exception as e:
            self.exception = e
        self.done = True

    def get_stdout(self):
        if not self.out_pipe:
            self.out_pipe = Queue()
        return self.out_pipe
        

class EOF:
    pass

class InterruptableTask(Task):
    def run(self):
        self.ready = False
        try:
            if self.in_pipe and self.started:
                # print("read from pipe")
                try:
                    r = self.body.send(self.in_pipe.get_nowait())
                except queue.Empty:
                    self.ready = True
                    return
            else:
                self.started = True
                r = next(self.body)
            self.result.append(r)
            if self.out_pipe:
                # print(f"put {r} in the pipe")
                self.out_pipe.put(r)
            self.ready = True
        except StopIteration as e:
            self.result.append(EOF)
            if self.out_pipe:
                self.out_pipe.put(EOF)
            self.done = True
            return
        except Exception as e:
            self.result.append(EOF)
            if self.out_pipe:
                self.out_pipe.put(EOF)
            self.exception = e
            self.done = True
            return

# def m():
#     for x in range(10):
#         time.sleep(.1)
#         yield x

# def p():
#     x = yield
#     while x != EOF:
#         print(f"i got an x: {x}")
#         time.sleep(1)
#         x = yield

# s = Sched()
# producer = InterruptableTask(m())
# consumer = InterruptableTask(p())
# consumer.in_pipe = producer.get_stdout()

# s.add(producer)
# s.add(consumer)

# s.run_all()
