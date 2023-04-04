import re
import os

from dominate import tags

import psynet.experiment
from psynet.prescreen import HeadphoneTest
from psynet.asset import CachedAsset, LocalStorage
from psynet.modular_page import VideoPrompt, SliderControl, PushButtonControl
from psynet.page import SuccessfulEndPage, ModularPage

from psynet.timeline import Timeline, Event
from psynet.trial.static import StaticTrial, StaticNode, StaticTrialMaker
from psynet.utils import get_logger

from .consent import consent
from .debrief import debriefing
from .instructions import instructions
from .questionnaire import questionnaire
from .calibration import AudioCalibration, BrightnessCalibration, CustomSlider
from .checks import headphone_test_intro, HearingImpairmentCheck, experiment_requirements

logger = get_logger()

DEBUG__ = True
TRIALS_PER_PARTICIPANT = 3 if DEBUG__ else 15

VOLUME_CALIBRATION_AUDIO = 'static/calibration/output.mp3'
BRIGHTNESS_CALIBRATION_IMAGE = 'static/calibration/brightness.jpg'
VIDEOS_DIR = 'static/videos'

VIDEOS = [vid for vid in os.listdir(VIDEOS_DIR) if vid.endswith('.mp4')]    # Just use a few videos for now

NODES = [
    StaticNode(
        definition={
            'duo': str(re.search('d(.*)_s', i).group(1)),   # Regex finds the trial info from the filename
            'session': str(re.search('_s(.*)_l', i).group(1)),
            'latency': str(re.search('_l(.*)_j', i).group(1)),
            'jitter': str(float(re.search('_j(.*)_kdelay', i).group(1)) / 10),
        },
        assets={
            'stimulus': CachedAsset(input_path=os.path.join(VIDEOS_DIR, i)),
        }
    )
    for i in VIDEOS
]


class SuccessTrial(StaticTrial):
    time_estimate = 30

    def get_text(self):
        text = [
            tags.h1("How successful was the performance?"),
        ]
        if DEBUG__:
            text.append(tags.p(
                    f"Duo: {self.node.definition['duo']}\n"
                    f"Session: {self.node.definition['session']}\n"
                    f"Latency: {self.node.definition['latency']}\n"
                    f"Jitter: {self.node.definition['jitter']}"
                )
            )
        return tags.div(*text)

    def show_trial(self, experiment, participant, debug_cutoff: float = 4):
        return ModularPage(
            "rating",
            VideoPrompt(
                video=self.node.assets['stimulus'],
                text=self.get_text(),
                mirrored=False,
                hide_when_finished=False,
                width='850px',
                controls=False,
                play_window=[0, debug_cutoff] if DEBUG__ else [0, None]
            ),
            CustomSlider(
                start_value=5,
                min_value=1,
                max_value=9,
                n_steps=9,
                snap_values=9,
                directional=False,
                include_labels=True,
                label_step=1
            ),
            events={
                "responseEnable": Event(is_triggered_by="promptStart"),
                "submitEnable": Event(is_triggered_by="promptEnd"),
            },
        )


class ScalesTrialMaker(StaticTrialMaker):
    give_end_feedback_passed = False

    def compute_bonus(self, score, passed):
        max_bonus = 0.40
        if score is None or score <= 0.0:
            bonus = 0.0
        else:
            bonus = max_bonus * score
        bonus = min(bonus, max_bonus)
        return bonus


class Exp(psynet.experiment.Experiment):
    label = "Networked performance success experiment"
    asset_storage = LocalStorage()
    variables = {
        "currency": "£",
        "wage_per_hour": 10,
        "window_width": 1024,
        "window_height": 1024,
    }
    if DEBUG__:
        timeline = Timeline(
            consent(),
            ScalesTrialMaker(
                id_="main_experiment",
                trial_class=SuccessTrial,
                nodes=NODES,
                expected_trials_per_participant=TRIALS_PER_PARTICIPANT,
                max_trials_per_participant=TRIALS_PER_PARTICIPANT,
                recruit_mode='n_trials',
                target_trials_per_node=10,
                allow_repeated_nodes=False,
                balance_across_nodes=True,
                check_performance_at_end=False,
                check_performance_every_trial=False,
                fail_trials_on_premature_exit=True,
                fail_trials_on_participant_performance_check=True,
                n_repeat_trials=0,
            ),
            SuccessfulEndPage(),
        )
    else:
        timeline = Timeline(
            consent(),
            HearingImpairmentCheck(),
            experiment_requirements(),
            AudioCalibration(audio=VOLUME_CALIBRATION_AUDIO),
            headphone_test_intro(),
            HeadphoneTest(),
            BrightnessCalibration(image=BRIGHTNESS_CALIBRATION_IMAGE),
            instructions(),
            ScalesTrialMaker(
                id_="main_experiment",
                trial_class=SuccessTrial,
                nodes=NODES,
                expected_trials_per_participant=TRIALS_PER_PARTICIPANT,
                max_trials_per_participant=TRIALS_PER_PARTICIPANT,
                recruit_mode='n_trials',
                target_trials_per_node=10,
                allow_repeated_nodes=False,
                balance_across_nodes=True,
                check_performance_at_end=False,
                check_performance_every_trial=False,
                fail_trials_on_premature_exit=True,
                fail_trials_on_participant_performance_check=True,
                n_repeat_trials=0,
            ),
            questionnaire(),
            debriefing(),
            SuccessfulEndPage(),
        )
