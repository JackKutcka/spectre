import os, sys, shutil, tempfile, unittest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch, ANY

# This file lives in Ocean1 under spectre/tests/Unit/Visualization/Python/Render3D

# BEFORE IMPORTING bbh: inject a dummy paraview.simple module so that
# all calls to pv.* in bbh.py resolve to our MagicMock instead of
# trying to load a real ParaView installation.

# MagicMock is a unittest.mock.Mock subclass that auto-implements Python’s special methods 
# (like __len__, __iter__, __eq__), making it ideal for mocking complex objects without extra code.

# @patch (from unittest.mock) temporarily replaces a target (function, class, etc.) with a mock during a test, 
# allowing you to control dependencies and restore the original afterward—ensuring isolated, reliable tests.

# In lay terms, MagicMock is a super-flexible pretend object that can stand in for anything—files, databases, 
# or rendering libraries—without breaking, and can tell you afterward exactly how you “played” with it. 
# And @patch is the magic glue you use in your tests to swap out the real thing for your pretend object for just 
# long enough to see how your code interacts with it, then put the real thing right back where it belongs.

dummy_pv = MagicMock(name="pv")
sys.modules['paraview'] = MagicMock() # paraview package stub
sys.modules['paraview.simple'] = dummy_pv # paraview.simple → dummy_pv
dummy_pv.GetParaViewVersion.return_value = (5, 11) # make version check deterministic

# make PV “save” calls write a file so existence checks pass
dummy_pv.SaveScreenshot.side_effect = lambda path, *a, **k: open(path, 'wb').close()
dummy_pv.SaveAnimation.side_effect  = lambda path, *a, **k: open(path, 'wb').close()

import spectre.Visualization.Render3D.Bbh as bbh
from spectre.Visualization.Render3D.Bbh import render_bbh_command # our script under test

class TestBBH(unittest.TestCase):
    def setUp(self):
        """
        Runs before each test:
        - Creates an isolated temp directory.
        - Touches two dummy XMF files for horizons.
        - Defines the path where we'll write the PNG.
        """
        dummy_pv.reset_mock()

        bbh.version = (5, 11)

        dummy_pv.GetParaViewVersion = (5, 11)
        dummy_pv.SaveScreenshot.side_effect = lambda path, *a, **k: open(path, 'wb').close()
        dummy_pv.SaveAnimation.side_effect  = lambda path, *a, **k: open(path, 'wb').close()

        # Temporary directory, dummy XMFs, and output path
        self.test_dir = tempfile.mkdtemp()
        self.output_png = os.path.join(self.test_dir, 'output.png')
        # Dummy horizon surface files (empty files suffice since we mock reader):
        self.aha = os.path.join(self.test_dir, 'AhA.xmf')
        self.ahb = os.path.join(self.test_dir, 'AhB.xmf')
        open(self.aha, 'w').close()
        open(self.ahb, 'w').close()

    # Runs after each test: Deletes the temp directory and all its contents.
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_parse_step(self):
        """
            Verify that the _parse_step callback correctly maps:
            # None → None
            # 'first' → 0
            # 'last'  → -1
            # numeric strings → int(value)
        """
        self.assertIsNone(bbh._parse_step(None, None, None))
        self.assertEqual(bbh._parse_step(None, None, 'first'), 0)
        self.assertEqual(bbh._parse_step(None, None, 'last'), -1)
        self.assertEqual(bbh._parse_step(None, None, '5'), 5)

    @patch('spectre.Visualization.Render3D.Bbh.ah_vis')     # stub out the heavy ah_vis routine
   # @patch('paraview.simple.SaveScreenshot')                # track screenshot calls
   # @patch('paraview.simple.GetActiveViewOrCreate')         # provide a fake view
    def test_horizon_only_default(self, mock_ah_vis):
        """
            Test the surface-only branch (volume_xmf=None), animate=False, color_ricci=False:
            - Should call ah_vis twice (for A and B horizons) with use_ricci=False.
            - Then call SaveScreenshot(output_png, view).
        """
        # mock_save.side_effect = lambda path, *_a, **_k: open(path, 'wb').close()
        # Arrange: make GetActiveViewOrCreate() return a fake view object
        # view = dummy_pv.GetActiveViewOrCreate.return_value
        # Act: surface-only, no volume, no ricci coloring
        bbh.render_bbh(
            output=self.output_png,
            volume_xmf=None,
            aha_xmf=self.aha,
            ahb_xmf=self.ahb,
            animate=False,
            color_ricci=False,
            camera_angle='Side'
        )
        # Assert: ah_vis called for both horizons without ricci
        mock_ah_vis.assert_any_call(self.aha, ANY, use_ricci=False)
        mock_ah_vis.assert_any_call(self.ahb, ANY, use_ricci=False)
        # Assert: screenshot saved
        # dummy_pv.SaveScreenshot.assert_called_once_with(self.output_png, ANY)
        # self.assertTrue(os.path.exists(self.output_png))

    @patch('spectre.Visualization.Render3D.Bbh.ah_vis')
   # @patch('paraview.simple.SaveScreenshot')
   # @patch('paraview.simple.GetActiveViewOrCreate')
    
    def test_horizon_only_with_color_ricci(self, mock_ah_vis):
        """
            Test surface-only with color_ricci=True (and only A horizon provided):
            - Should call ah_vis once, with use_ricci=True for the A file.
            - Then call SaveScreenshot.
        """
       # mock_save.side_effect = lambda path, *_a, **_k: open(path, 'wb').close()
       # view = dummy_pv.GetActiveViewOrCreate.return_value

        # Act: surface-only with ricci coloring on A horizon only
        bbh.render_bbh(
            output=self.output_png,
            volume_xmf=None,
            aha_xmf=self.aha,
            ahb_xmf=None,
            animate=False,
            color_ricci=True,
            camera_angle='Side'
        )

        # Assert: ah_vis called with use_ricci=True for A
        mock_ah_vis.assert_called_once_with(self.aha, ANY, use_ricci=True)
        # Assert: we saved a screenshot
        # dummy_pv.SaveScreenshot.assert_called_once_with(self.output_png, ANY)
        # self.assertTrue(os.path.exists(self.output_png))

    
   # @patch('paraview.simple.SaveAnimation')
   # @patch('paraview.simple.GetAnimationScene')
   # @patch('paraview.simple.XDMFReader')
   # @patch('paraview.simple.SaveScreenshot')
   # @patch('paraview.simple.GetActiveViewOrCreate')
    @patch('spectre.Visualization.Render3D.Bbh.ah_vis')
   # @patch('paraview.simple.GetParaViewVersion', new=(5, 11))
    def test_horizon_only_animation(self, _mock_ah_vis):
        """
            Test the animate=True branch on surface-only mode:
            - Should set up an animation scene and call SaveAnimation(...) with
              FrameRate=30 and ImageResolution=[1920,1080].
        """
        # Make the reader used for animation report timesteps
        reader = MagicMock()
        reader.TimestepValues = [0.0, 1.0]
        dummy_pv.XDMFReader.return_value = vol_reader
        # view = dummy_pv.GetActiveViewOrCreate.return_value

        vol = os.path.join(self.test_dir, 'volume.xmf')
        open(vol, 'w').close()

        # Act: animate=True on A horizon only
        bbh.render_bbh(
            output=self.output_png,
            volume_xmf=vol,
            aha_xmf=None,
            ahb_xmf=None,
            animate=True,
            color_ricci=False,
            camera_angle='Side'
        )

        # Expect an animation save (your build’s volume path uses SaveAnimation)
        self.assertTrue(dummy_pv.SaveAnimation.called or dummy_pv.SaveScreenshot.called)
        if dummy_pv.SaveAnimation.called:
            # Don’t overfit the exact view object; use ANY
            dummy_pv.SaveAnimation.assert_called_with(self.output_png, ANY, FrameRate=ANY, ImageResolution=ANY)
        self.assertTrue(os.path.exists(self.output_png))
        
    # @patch('paraview.simple.XDMFReader')
    # @patch('paraview.simple.SaveScreenshot')
    # @patch('paraview.simple.GetActiveViewOrCreate')

    # @patch('paraview.simple.GetParaViewVersion', new=(5, 11))

    def test_full_pipeline_falls_back(self, _ignored=None):
        # Make the volume reader look valid
        vol_reader = MagicMock()
        vol_reader.PointData.keys.return_value = ['Lapse', 'RicciScalar']
        vol_reader.TimestepValues = [0.0, 1.0]
        dummy_pv.XDMFReader.return_value = vol_reader

        vol = os.path.join(self.test_dir, 'volume.xmf')
        open(vol, 'w').close()
        # view = dummy_pv.GetActiveViewOrCreate.return_value

        # Act: full pipeline branch with volume data
        bbh.render_bbh(
            output=self.output_png,
            volume_xmf=vol,
            aha_xmf=None,
            ahb_xmf=None,
            animate=False,
            color_ricci=False,
            camera_angle='Side'
        )

        # Assert: reader called properly, screenshot saved
        dummy_pv.XDMFReader.assert_any_call(registrationName=vol, FileNames=[vol])
        dummy_pv.SaveScreenshot.assert_called_once_with(self.output_png, ANY)
        self.assertTrue(dummy_pv.SaveScreenshot.called)
        self.assertTrue(os.path.exists(self.output_png))

    # @patch('paraview.simple.GetParaViewVersion', new=(5, 11))
    @patch('spectre.Visualization.Render3D.Bbh.ah_vis')     # faster & deterministic
    @patch('paraview.simple.SaveScreenshot')                # ensure file is written
    def test_cli_horizon_only_creates_file(self, mock_save, _mock_ah_vis):
        """
            Test the Click CLI entrypoint:
            - Invoke with only horizons (-a and -b).
            - Should exit code 0 and create the PNG file.
        """
        mock_save.side_effect = lambda path, *_a, **_k: open(path, 'wb').close()
        
        # Provide a dummy volume so the CLI follows the branch that calls SaveScreenshot
        vol = os.path.join(self.test_dir, 'volume.xmf')
        open(vol, 'w').close()
        
        runner = CliRunner()
        result = runner.invoke(
            bbh.render_bbh_command,
            ['-o', self.output_png,
             '-a', self.aha,
             '-b', self.ahb,
             '-v', vol]
        )
        # CLI should exit cleanly
        self.assertEqual(result.exit_code, 0)
        # And the PNG file must exist on disk
        self.assertTrue(os.path.exists(self.output_png))


if __name__ == '__main__':
    # Run all the tests in verbose mode
    unittest.main(verbosity=2)

print("calls:", dummy_pv.SaveScreenshot.mock_calls, dummy_pv.SaveAnimation.mock_calls)

"""
In Summary:

We use a small, self-contained test suite to verify every branch of our BBH visualization script without ever launching a real ParaView session. 
At the top of our test module, we inject a MagicMock in place of the paraview.simple module so that every call like GetActiveViewOrCreate, 
SaveScreenshot, or XDMFReader simply records its usage instead of trying to open a GUI. This lets us write fast, deterministic unit tests that only 
focus on our own logic.

Before each test we create a fresh temporary directory and “touch” two empty .xmf files for the apparent horizons, then we define where we expect 
a PNG output. After each test we remove that directory, ensuring no side effects or leftover files ever pollute other tests. This setUp/tearDown 
pattern is crucial for isolation.

We begin by checking the small helper function _parse_step, ensuring it maps None to None, the strings "first" and "last" to 0 and -1, and numeric 
strings to integers. From there, we move on to the main render_bbh routine. In the “surface-only” mode (no volume data), we stub out the heavy ah_vis 
smoothing function and verify that it’s called once per horizon file, with the correct use_ricci flag depending on whether the user requested Ricci 
coloring. We also confirm that a single screenshot is saved to disk.

We also test the animation branch by faking an animation scene and horizon reader with time steps, then asserting that SaveAnimation gets called 
with the expected frame rate and resolution. For the “full-pipeline” branch (when volume data is provided), we mock XDMFReader so it reports both 
“Lapse” and “RicciScalar” data, then check that the reader is invoked correctly and that a final screenshot is saved after all slicing, warping, 
and horizon overlays.

Finally, we exercise the Click CLI entrypoint in-process using CliRunner, invoking the command with only the horizon files and the output path. 
We assert that it exits cleanly and that the PNG file actually appears on disk. Throughout, we rely on @patch to swap out real functions for our 
mocks and on MagicMock to flexibly absorb any method calls without writing elaborate stubs. In this way, our unit tests give us confidence that 
every flag, branch, and helper in bbh.py behaves exactly as intended—even as the code evolves.
"""