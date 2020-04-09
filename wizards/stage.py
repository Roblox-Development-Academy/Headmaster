class Stage:
    def __init__(self, stage_type, response_func, message, messages=None):
        """
        :param stage_type: Member of enum StageType
        :param response_func: Coroutine that takes Wizard and Message objects that handles Wizard responses. It returns
        whether or not to stop receiving responses for the current stage. Defaults to false.
        :param message: The message parameters in a tuple that will be sent for this stage of the Wizard
        :param messages: A list of any additional messages to send
        """
        # TODO - Add a list of emojis the bot automatically reacts with to each stage/message somehow - custom
        #  message object that's subclass of discord.Message?
        #  Or convert an argument like stage_type and make them 2 different properties. stage_type -> reaction_emojis.
        #  Or make ReactionStage and TextStage different subclasses of stage w/ different args

        # TODO - Consider persistent stages 
        self.type = stage_type
        self.respond = response_func
        self.messages = messages or []
        self.messages.append(message)
        self.messages.extend(messages)
        self.cancellable = True
        self.timeout = 300  # Time in seconds before disabling

