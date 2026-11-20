// Exercises the real SD line reader against a bounded host file double.
#include <assert.h>
#include <stddef.h>
#include <string.h>

#include "sd-utils.h"

int main() {
  char input[263];
  size_t input_size = 0;
  memset(input + input_size, 'A', 127);
  input_size += 127;
  input[input_size++] = '\n';
  memset(input + input_size, 'B', 128);
  input_size += 128;
  input[input_size++] = '\n';
  memcpy(input + input_size, "next\n", 5);
  input_size += 5;

  SdFile file;
  file.SetInput(input, input_size);

  char* line = read_line(file);
  assert(line != nullptr && strlen(line) == 127);
  assert(line[0] == 'A' && line[126] == 'A');

  line = read_line(file);
  assert(line != nullptr && strlen(line) == 127);
  assert(line[0] == 'B' && line[126] == 'B');
  assert(strcmp(read_line(file), "next") == 0);
  assert(read_line(file) == nullptr);
}
