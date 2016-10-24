import sublime
import sublime_plugin

import subprocess
import io
from os import path

class TerraformFmtOnSave(sublime_plugin.EventListener):
  def on_pre_save(self, view):
    if not is_terraform_source(view):
      return

    view.run_command('terraform_fmt')

class TerraformFmt(sublime_plugin.TextCommand):
  def is_enabled(self):
    fmt_enabled = sublime.load_settings('Terraform.sublime-settings').get('format_on_save', True)
    return fmt_enabled and is_terraform_source(self.view)

  def run(self, edit):
    res = self.run_fmt()
    if res is None:
      return

    # Replace the buffer with terraform fmt output.
    self.view.replace(edit, sublime.Region(0, self.view.size()), res)

    # Hide errors panel
    self.view.window().run_command('hide_panel', { 'panel': 'output.terraform_syntax_errors' })

  def run_fmt(self):
    with self.popen_terraform_fmt() as p:
      stdout, stderr = [str(s, self.encoding()) for s in p.communicate(input=self.view_content_bytes())]

      # Something went wrong
      if p.returncode != 0:
        stderr = '{}: {}'.format(path.basename(self.view.file_name()), stderr)
        self.show_syntax_errors(stderr)
        return None

      return stdout

  def popen_terraform_fmt(self):
    cmd = sublime.load_settings('Terraform.sublime-settings').get('terraform_path', 'terraform')
    return subprocess.Popen(
      [cmd, 'fmt', '-no-color', '-'],
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      stdin=subprocess.PIPE)

  def view_content_bytes(self):
    region = sublime.Region(0, self.view.size())
    buf = self.view.substr(region)
    return bytes(buf, self.encoding())

  def encoding(self):
    enc = self.view.encoding()

    # When a selection is actuve the encoding is undefined. Fall back to utf-8
    # by default.
    if enc == "Undefined":
      return "UTF-8"

    return enc

  def show_syntax_errors(self, errors):
    window = self.view.window()
    panel = window.create_output_panel('terraform_syntax_errors')
    panel.set_syntax_file('Packages/Text/Plain text.tmLanguage')
    panel.settings().set('line_numbers', False)
    panel.settings().set('result_file_regex', '^(.+):\s.+At\s(\d+):(\d+):\s(.*)$')
    panel.settings().set('result_base_dir', path.dirname(self.view.file_name()))
    panel.set_scratch(True)
    panel.set_read_only(False)
    panel.run_command('append', {'characters': errors})
    panel.set_read_only(True)
    window.run_command('show_panel', { 'panel': 'output.terraform_syntax_errors' })

def is_terraform_source(view):
  tp = 0
  sel = view.sel()
  if sel is not None:
    tp = sel[0].begin()

  return view.match_selector(tp, 'source.terraform')
